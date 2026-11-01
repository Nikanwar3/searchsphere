"""A term -> postings inverted index with O(1) term lookups.

Layout
------
``_postings``:  term -> {doc_id: term_frequency}
``_doc_terms``: doc_id -> {term: term_frequency}   (reverse map, enables O(unique terms
                in the document) deletion instead of an O(vocabulary) full scan)
``_doc_lengths``: doc_id -> token count (needed by BM25's length normalization)

This class is a plain in-memory data structure and is **not thread-safe** on its
own; concurrent mutation must be serialized by the caller (see
``app.services.index_manager.IndexManager``, which wraps it with a lock).
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List, Mapping


class InvertedIndex:
    def __init__(self) -> None:
        self._postings: Dict[str, Dict[int, int]] = {}
        self._doc_terms: Dict[int, Dict[str, int]] = {}
        self._doc_lengths: Dict[int, int] = {}
        self._total_length: int = 0

    def add_document(self, doc_id: int, tokens: Iterable[str]) -> None:
        """Index (or re-index) a document under ``doc_id``.

        Time: O(u) where u is the number of unique terms in the document
        (building the term-frequency map is O(t) for t tokens, dominating
        when the document has many repeated terms).
        Space: O(u) new entries in the postings map.
        """
        if doc_id in self._doc_terms:
            self.remove_document(doc_id)

        term_freqs = Counter(tokens)
        token_count = sum(term_freqs.values())

        for term, freq in term_freqs.items():
            self._postings.setdefault(term, {})[doc_id] = freq

        self._doc_terms[doc_id] = dict(term_freqs)
        self._doc_lengths[doc_id] = token_count
        self._total_length += token_count

    def remove_document(self, doc_id: int) -> bool:
        """Remove a document from the index.

        Time: O(u) where u is the number of unique terms the document
        contributed (we only touch postings lists the document appears in,
        not the whole vocabulary).
        """
        term_freqs = self._doc_terms.pop(doc_id, None)
        if term_freqs is None:
            return False

        self._total_length -= self._doc_lengths.pop(doc_id, 0)
        for term in term_freqs:
            postings = self._postings.get(term)
            if postings is None:
                continue
            postings.pop(doc_id, None)
            if not postings:
                del self._postings[term]
        return True

    def get_postings(self, term: str) -> Mapping[int, int]:
        """O(1) average lookup of a term's posting list."""
        return self._postings.get(term, {})

    def document_frequency(self, term: str) -> int:
        """Number of documents containing ``term``. O(1) (via dict length)."""
        postings = self._postings.get(term)
        return len(postings) if postings else 0

    def document_length(self, doc_id: int) -> int:
        return self._doc_lengths.get(doc_id, 0)

    def terms_for_document(self, doc_id: int) -> Mapping[str, int]:
        return self._doc_terms.get(doc_id, {})

    def contains(self, doc_id: int) -> bool:
        return doc_id in self._doc_terms

    @property
    def document_count(self) -> int:
        return len(self._doc_terms)

    @property
    def average_document_length(self) -> float:
        n = self.document_count
        return (self._total_length / n) if n else 0.0

    def vocabulary(self) -> List[str]:
        return list(self._postings.keys())

    def candidate_documents(self, terms: Iterable[str]) -> set[int]:
        """Union of documents containing at least one of ``terms``.

        Time: O(sum of df(term) for term in terms) -- this is the key
        complexity win of an inverted index over a linear scan: a query
        touches only documents that actually contain a query term, not
        every document in the corpus.
        """
        candidates: set[int] = set()
        for term in terms:
            candidates.update(self._postings.get(term, {}).keys())
        return candidates
