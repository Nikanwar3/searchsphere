"""Search orchestration: cache lookup -> BM25 ranking -> cache fill.

Kept deliberately thin -- all algorithmic work lives in app.core, all state
lives in IndexManager/ResultCache. This function is the only place that
wires caching into the query path, which is what makes
``benchmarks/bench_cache.py`` (cached vs. uncached latency) meaningful: it
exercises exactly this function.
"""
from __future__ import annotations

from typing import Any, Dict

from app.services.index_manager import IndexManager
from app.storage.cache import ResultCache

SNIPPET_LENGTH = 220


def _snippet(body: str) -> str:
    body = body.strip()
    if len(body) <= SNIPPET_LENGTH:
        return body
    return body[:SNIPPET_LENGTH].rsplit(" ", 1)[0] + "..."


def search(
    *,
    index_manager: IndexManager,
    cache: ResultCache,
    query: str,
    offset: int,
    limit: int,
) -> Dict[str, Any]:
    cache_key = cache.search_key(query, offset, limit)
    cached = cache.get_json(cache_key)
    if cached is not None:
        return {**cached, "cache_hit": True}

    records, scores, total = index_manager.search(query, offset=offset, limit=limit)
    results = [
        {
            "doc_id": record.doc_id,
            "title": record.title,
            "snippet": _snippet(record.body),
            "score": round(score, 6),
        }
        for record, score in zip(records, scores)
    ]
    response = {
        "query": query,
        "total": total,
        "offset": offset,
        "limit": limit,
        "results": results,
    }
    cache.set_json(cache_key, response)
    return {**response, "cache_hit": False}
