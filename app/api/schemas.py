"""Request/response contracts. Pydantic enforces input validation (empty
strings, oversized payloads, out-of-range pagination) before a request ever
reaches business logic.
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, field_validator


class DocumentCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    body: str = Field(..., min_length=1, max_length=100_000)

    @field_validator("title", "body")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank or whitespace-only")
        return value


class DocumentCreateResponse(BaseModel):
    doc_id: int
    title: str
    created: bool = Field(..., description="False if identical content already existed")


class DocumentResponse(BaseModel):
    doc_id: int
    title: str
    body: str


class SearchResultItem(BaseModel):
    doc_id: int
    title: str
    snippet: str
    score: float


class SearchResponse(BaseModel):
    query: str
    total: int
    offset: int
    limit: int
    cache_hit: bool
    results: List[SearchResultItem]


class AutocompleteSuggestion(BaseModel):
    term: str
    frequency: int


class AutocompleteResponse(BaseModel):
    prefix: str
    cache_hit: bool
    suggestions: List[AutocompleteSuggestion]
