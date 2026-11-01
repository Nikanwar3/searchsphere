"""Document ingestion: persist to Postgres, update the in-memory index, and
invalidate cached search/autocomplete results.

Ordering matters: we only mutate the in-memory index and bump the cache
version *after* the database commit succeeds, so a failed write never
leaves the index ahead of the system of record. On duplicate content
(detected by ``repository.create_document`` via the unique content-hash
constraint) neither the index nor the cache is touched, since nothing
actually changed.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.services.index_manager import IndexManager
from app.storage import repository
from app.storage.cache import ResultCache


@dataclass
class IngestionOutcome:
    doc_id: int
    title: str
    created: bool  # False => duplicate of existing content, no new document


def ingest_document(
    db: Session, *, index_manager: IndexManager, cache: ResultCache, title: str, body: str
) -> IngestionOutcome:
    result = repository.create_document(db, title=title, body=body)

    if result.created:
        index_manager.add_document(result.document.id, result.document.title, result.document.body)
        cache.invalidate()

    return IngestionOutcome(doc_id=result.document.id, title=result.document.title, created=result.created)


def delete_document(db: Session, *, index_manager: IndexManager, cache: ResultCache, doc_id: int) -> bool:
    deleted = repository.delete_document(db, doc_id)
    if deleted:
        index_manager.remove_document(doc_id)
        cache.invalidate()
    return deleted
