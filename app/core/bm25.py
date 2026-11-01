"""BM25 (Okapi) relevance ranking over an :class:`InvertedIndex`.

BM25 scores a document D against a query Q as::

    score(D, Q) = sum_{t in Q} IDF(t) * f(t, D) * (k1 + 1)
                  -----------------------------------------
                  f(t, D) + k1 * (1 - b + b * |D| / avgdl)

where ``f(t, D)`` is the term frequency of t in D, ``|D|`` is D's token
count, ``avgdl`` is the corpus average document length, and::

    IDF(t) = ln((N - df(t) + 0.5) / (df(t) + 0.5) + 1)

``k1`` controls term-frequency saturation (higher = less saturation,
repeated terms keep contributing) and ``b`` controls length normalization
(0 = none, 1 = full normalization by document length). 1.5 / 0.75 are the
standard defaults from the Okapi BM25 literature and Lucene/Elasticsearch.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List

from app.core.inverted_index import InvertedIndex


@dataclass(frozen=True)
class BM25Params:
    k1: float = 1.5
    b: float = 0.75


class BM25Ranker:
    def __init__(self, index: InvertedIndex, params: BM25Params | None = None) -> None:
        self._index = index
        self._params = params or BM25Params()

    def idf(self, term: str) -> float:
        """Inverse document frequency. O(1) given the index's O(1) df lookup."""
        n = self._index.document_count
        df = self._index.document_frequency(term)
        if n == 0:
            return 0.0
        return math.log((n - df + 0.5) / (df + 0.5) + 1.0)

    def score_documents(self, query_terms: Iterable[str]) -> Dict[int, float]:
        """Score every candidate document (one containing >=1 query term).

        Time: O(sum over distinct query terms of df(term)) -- we only ever
        touch postings for documents that contain a query term, which is
        what makes indexed search sub-linear in corpus size. A linear-scan
        baseline is always O(N * |Q|) regardless of how selective the
        query is; see benchmarks/bench_search_vs_linear.py for a measured
        comparison.
        Space: O(number of candidate documents).
        """
        terms = list(query_terms)
        if not terms or self._index.document_count == 0:
            return {}

        k1, b = self._params.k1, self._params.b
        avgdl = self._index.average_document_length or 1.0
        scores: Dict[int, float] = {}

        for term in terms:
            postings = self._index.get_postings(term)
            if not postings:
                continue
            term_idf = self.idf(term)
            if term_idf <= 0:
                continue
            for doc_id, freq in postings.items():
                doc_len = self._index.document_length(doc_id)
                denom = freq + k1 * (1 - b + b * (doc_len / avgdl))
                contribution = term_idf * (freq * (k1 + 1)) / denom
                scores[doc_id] = scores.get(doc_id, 0.0) + contribution

        return scores

    def score_documents_linear_scan(
        self, query_terms: Iterable[str], all_document_ids: Iterable[int]
    ) -> Dict[int, float]:
        """Reference baseline: identical BM25 math, but evaluates every
        document in the corpus instead of only index candidates.

        Time: O(N * |Q|) where N is the corpus size -- used purely to
        benchmark the speedup the inverted index provides (see
        benchmarks/bench_search_vs_linear.py); never used on the live
        query path.
        """
        terms = list(query_terms)
        if not terms or self._index.document_count == 0:
            return {}

        k1, b = self._params.k1, self._params.b
        avgdl = self._index.average_document_length or 1.0
        idfs = {term: self.idf(term) for term in terms}
        scores: Dict[int, float] = {}

        for doc_id in all_document_ids:
            doc_terms = self._index.terms_for_document(doc_id)
            if not doc_terms:
                continue
            doc_len = self._index.document_length(doc_id)
            total = 0.0
            for term in terms:
                freq = doc_terms.get(term, 0)
                if freq == 0:
                    continue
                denom = freq + k1 * (1 - b + b * (doc_len / avgdl))
                total += idfs[term] * (freq * (k1 + 1)) / denom
            if total > 0:
                scores[doc_id] = total

        return scores
