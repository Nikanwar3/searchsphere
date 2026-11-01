"""Three Top-K selection strategies over a {doc_id: score} map.

All three return the same thing -- the k highest-scoring (doc_id, score)
pairs, sorted descending by score and then by doc_id ascending for a
deterministic tie-break -- but with different complexity:

* ``top_k_full_sort``      O(n log n) time, O(n) space -- sorts everything.
* ``top_k_heapq_nlargest`` O(n log k) time, O(n) space -- stdlib's heap-based
  nlargest; still allocates an O(n) list of items to heapify from.
* ``top_k_bounded_heap``   O(n log k) time, O(k) space -- a hand-rolled
  bounded min-heap that only ever holds k elements: push while the heap
  has room, otherwise compare against the current minimum and replace in
  O(log k) when the candidate is larger. This is the version the live
  search path uses, since both the asymptotic time *and* space scale with
  k rather than n -- the win is largest when the result set n is huge and
  only a small k is requested, which is the common "page 1 of search
  results" case.

benchmarks/bench_topk.py measures all three against the same inputs.
"""
from __future__ import annotations

import heapq
from typing import Dict, List, Tuple

ScoredDoc = Tuple[int, float]


def _sort_key(item: ScoredDoc) -> Tuple[float, int]:
    doc_id, score = item
    return (-score, doc_id)


def top_k_full_sort(scores: Dict[int, float], k: int) -> List[ScoredDoc]:
    if k <= 0:
        return []
    return sorted(scores.items(), key=_sort_key)[:k]


def top_k_heapq_nlargest(scores: Dict[int, float], k: int) -> List[ScoredDoc]:
    if k <= 0:
        return []
    # The key must encode the FULL tie-break (score, then doc_id), not just
    # score: nlargest's internal selection of *which* items survive at a tied
    # boundary depends on key ordering alone, so a score-only key makes the
    # chosen set (not just its final order) vary arbitrarily with k whenever
    # many items tie -- which breaks pagination (page N+1 could repeat or
    # skip rows from page N). Negating doc_id makes "smaller doc_id" sort as
    # "larger key", matching our documented ascending-doc_id tie-break.
    items = heapq.nlargest(k, scores.items(), key=lambda kv: (kv[1], -kv[0]))
    return sorted(items, key=_sort_key)


def top_k_bounded_heap(scores: Dict[int, float], k: int) -> List[ScoredDoc]:
    if k <= 0:
        return []

    # Min-heap over (score, -doc_id): this makes heap[0] -- the eviction
    # candidate -- the globally worst kept item (lowest score, and among
    # ties the LARGEST doc_id), which matches the ascending-doc_id tie-break
    # used everywhere else. Encoding doc_id as -doc_id is what makes plain
    # tuple comparison do the right thing; comparing raw (score, doc_id)
    # instead would evict the smallest doc_id first on a tie and make the
    # selected set (not just the order) depend on k, breaking pagination.
    heap: List[Tuple[float, int]] = []
    for doc_id, score in scores.items():
        entry = (score, -doc_id)
        if len(heap) < k:
            heapq.heappush(heap, entry)
        elif entry > heap[0]:
            heapq.heapreplace(heap, entry)

    results = [(-neg_doc_id, score) for score, neg_doc_id in heap]
    results.sort(key=_sort_key)
    return results


def paginate_top_k(
    scores: Dict[int, float], *, offset: int, limit: int
) -> Tuple[List[ScoredDoc], int]:
    """Return a page of ``limit`` results starting at ``offset``, plus the
    total number of matching documents (for building pagination metadata).

    Time: O(n log(offset + limit)) via the bounded heap, which is far
    cheaper than fully sorting n candidates when offset+limit << n.
    """
    total = len(scores)
    if limit <= 0 or offset >= total:
        return [], total
    window = top_k_bounded_heap(scores, offset + limit)
    return window[offset : offset + limit], total
