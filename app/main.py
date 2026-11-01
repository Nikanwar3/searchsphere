"""FastAPI application factory.

On startup we create the Postgres schema if missing and rehydrate the
in-memory index from the documents already in the database -- Postgres is
the system of record, the in-memory index is a derived, rebuildable view
over it.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.deps import index_manager_dependency
from app.api.routes_autocomplete import router as autocomplete_router
from app.api.routes_documents import router as documents_router
from app.api.routes_search import router as search_router
from app.config import get_settings
from app.services.index_manager import DocRecord
from app.storage import repository
from app.storage.db import Base, SessionLocal, engine

logger = logging.getLogger("searchsphere")


def _rebuild_index_from_database() -> None:
    Base.metadata.create_all(bind=engine)
    index_manager = index_manager_dependency()
    db = SessionLocal()
    try:
        documents = repository.list_all_documents(db)
        records = [DocRecord(doc_id=d.id, title=d.title, body=d.body) for d in documents]
        index_manager.rebuild(records)
        logger.info("Rebuilt in-memory index with %d documents", len(records))
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _rebuild_index_from_database()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.api_title,
        description=(
            "SearchSphere: a from-scratch inverted index, BM25 ranker, and "
            "trie-based autocomplete behind a FastAPI search service."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(documents_router)
    app.include_router(search_router)
    app.include_router(autocomplete_router)

    @app.get("/health", tags=["health"])
    def health() -> dict:
        index_manager = index_manager_dependency()
        return {"status": "ok", "indexed_documents": index_manager.document_count}

    @app.exception_handler(Exception)
    def unhandled_exception_handler(request, exc):  # noqa: ANN001
        logger.exception("Unhandled error on %s %s", request.method, request.url)
        return JSONResponse(status_code=500, content={"detail": "internal server error"})

    return app


app = create_app()
