from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import cache_dependency, get_db, index_manager_dependency
from app.api.schemas import DocumentCreateRequest, DocumentCreateResponse, DocumentResponse
from app.services import ingestion_service
from app.services.index_manager import IndexManager
from app.storage import repository
from app.storage.cache import ResultCache

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentCreateResponse, status_code=status.HTTP_201_CREATED)
def ingest_document(
    payload: DocumentCreateRequest,
    db: Session = Depends(get_db),
    index_manager: IndexManager = Depends(index_manager_dependency),
    cache: ResultCache = Depends(cache_dependency),
) -> DocumentCreateResponse:
    outcome = ingestion_service.ingest_document(
        db, index_manager=index_manager, cache=cache, title=payload.title, body=payload.body
    )
    return DocumentCreateResponse(doc_id=outcome.doc_id, title=outcome.title, created=outcome.created)


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db)) -> DocumentResponse:
    doc = repository.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"document {doc_id} not found")
    return DocumentResponse(doc_id=doc.id, title=doc.title, body=doc.body)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    index_manager: IndexManager = Depends(index_manager_dependency),
    cache: ResultCache = Depends(cache_dependency),
) -> None:
    deleted = ingestion_service.delete_document(db, index_manager=index_manager, cache=cache, doc_id=doc_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"document {doc_id} not found")
