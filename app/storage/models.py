"""The single persisted entity: a searchable document.

``content_hash`` is a SHA-256 of the normalized (title, body) pair with a
unique index. It is the mechanism behind duplicate-document detection: a
second ingestion of identical content hits the unique constraint and the
repository turns that into an idempotent "already exists" response instead
of a second row (see ``app.storage.repository.create_document``).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_documents_created_at", "created_at"),
    )
