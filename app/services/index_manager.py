"""The in-memory search index, held as process-wide shared state.

A single ``IndexManager`` instance (see ``get_index_manager``) owns the
``InvertedIndex``, the autocomplete ``Trie``, and a small ``doc_store`` used
to render result snippets without a DB round-trip per search hit.

Concurrency model: all reads and writes go through one ``threading.RLock``.
This serializes access but guarantees every search/autocomplete call sees a
consistent snapshot of the index -- never a document that is half-added
(postings updated but doc_store not yet, or vice versa). For this project's
scale (demonstrating correct data structures and APIs, not maximum
read throughput) a single lock is the right trade-off: it is trivially
correct and easy to reason about. The scalability section of the README
discusses the production alternative -- copy-on-write snapshots published
behind an atomic pointer swap, which lets reads proceed lock-free while a
writer builds the next version -- and when that complexity would start to
pay for itself (write-heavy workloads or many CPU cores contending on the
lock).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from app.core.bm25 import BM25Params, BM25Ranker
from app.core.inverted_index import InvertedIndex
from app.core.tokenizer import tokenize
from app.core.topk import paginate_top_k
from app.core.trie import Trie
from app.config import get_settings


@dataclass(frozen=True)
class DocRecord:
    doc_id: int
    title: str
    body: str


class IndexManager:
    def __init__(self, bm25_params: Optional[BM25Params] = None) -> None:
        self._lock = threading.RLock()
        self._index = InvertedIndex()
        self._trie = Trie()
        self._doc_store: Dict[int, DocRecord] = {}
        self._ranker = BM25Ranker(self._index, bm25_params or BM25Params())

    def add_document(self, doc_id: int, title: str, body: str) -> None:
        tokens = tokenize(f"{title} {body}")
        with self._lock:
            self._index.add_document(doc_id, tokens)
            self._doc_store[doc_id] = DocRecord(doc_id, title, body)
            for term in set(tokens):
                self._trie.insert(term, weight=1)

    def remove_document(self, doc_id: int) -> bool:
        with self._lock:
            existing_terms = set(self._index.terms_for_document(doc_id).keys())
            removed = self._index.remove_document(doc_id)
            if not removed:
                return False
            self._doc_store.pop(doc_id, None)
            for term in existing_terms:
                self._trie.remove_weight(term, weight=1)
            return True

    def search(self, query: str, *, offset: int, limit: int) -> Tuple[List[DocRecord], List[float], int]:
        """Return (records, scores, total_matches) for the requested page."""
        terms = tokenize(query)
        with self._lock:
            if not terms:
                return [], [], 0
            scores = self._ranker.score_documents(terms)
            page, total = paginate_top_k(scores, offset=offset, limit=limit)
            records = [self._doc_store[doc_id] for doc_id, _ in page if doc_id in self._doc_store]
            score_values = [score for doc_id, score in page if doc_id in self._doc_store]
            return records, score_values, total

    def autocomplete(self, prefix: str, limit: int) -> List[Tuple[str, int]]:
        normalized = prefix.strip().lower()
        if not normalized:
            return []
        with self._lock:
            return self._trie.suggest(normalized, limit=limit)

    @property
    def document_count(self) -> int:
        with self._lock:
            return self._index.document_count

    def rebuild(self, documents: List[DocRecord]) -> None:
        """Replace the index wholesale -- used on application startup to
        hydrate the in-memory index from PostgreSQL, the system of record.
        """
        with self._lock:
            self._index = InvertedIndex()
            self._trie = Trie()
            self._doc_store = {}
            self._ranker = BM25Ranker(self._index, self._ranker._params)
            for record in documents:
                tokens = tokenize(f"{record.title} {record.body}")
                self._index.add_document(record.doc_id, tokens)
                self._doc_store[record.doc_id] = record
                for term in set(tokens):
                    self._trie.insert(term, weight=1)


@lru_cache
def get_index_manager() -> IndexManager:
    settings = get_settings()
    return IndexManager(BM25Params(k1=settings.bm25_k1, b=settings.bm25_b))
