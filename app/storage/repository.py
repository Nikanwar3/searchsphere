"""Document persistence, including race-safe duplicate detection.

Duplicate handling relies on the database's unique constraint on
``content_hash`` rather than a check-then-insert in Python: two concurrent
requests ingesting the same content can both pass a pre-check, but only one
INSERT can win the unique index, so we attempt the insert, catch the
resulting ``IntegrityError``, and fetch-and-return the winning row. This is
the standard way to make "insert if not exists" safe under concurrency
without taking an explicit table lock.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.storage.models import Document


def compute_content_hash(title: str, body: str) -> str:
    normalized = f"{title.strip().lower()}\n{body.strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass
class IngestResult:
    document: Document
    created: bool  # False => this content already existed (duplicate)


def create_document(db: Session, *, title: str, body: str) -> IngestResult:
    content_hash = compute_content_hash(title, body)

    doc = Document(title=title, body=body, content_hash=content_hash)
    db.add(doc)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = get_document_by_hash(db, content_hash)
        if existing is None:
            # Extremely unlikely (constraint violated by something other than
            # content_hash), but fail loudly rather than mask the error.
            raise
        return IngestResult(document=existing, created=False)

    db.refresh(doc)
    return IngestResult(document=doc, created=True)


def get_document(db: Session, doc_id: int) -> Optional[Document]:
    return db.get(Document, doc_id)


def get_document_by_hash(db: Session, content_hash: str) -> Optional[Document]:
    stmt = select(Document).where(Document.content_hash == content_hash)
    return db.execute(stmt).scalar_one_or_none()


def delete_document(db: Session, doc_id: int) -> bool:
    doc = db.get(Document, doc_id)
    if doc is None:
        return False
    db.delete(doc)
    db.commit()
    return True


def list_all_documents(db: Session) -> Sequence[Document]:
    """Used only to (re)build the in-memory index on startup."""
    stmt = select(Document).order_by(Document.id)
    return db.execute(stmt).scalars().all()


def count_documents(db: Session) -> int:
    return db.query(Document).count()
