"""Prefix autocomplete, cached the same way as search (see search_service)."""
from __future__ import annotations

from typing import Any, Dict

from app.services.index_manager import IndexManager
from app.storage.cache import ResultCache


def autocomplete(
    *, index_manager: IndexManager, cache: ResultCache, prefix: str, limit: int
) -> Dict[str, Any]:
    cache_key = cache.autocomplete_key(prefix, limit)
    cached = cache.get_json(cache_key)
    if cached is not None:
        return {**cached, "cache_hit": True}

    suggestions = index_manager.autocomplete(prefix, limit)
    response = {
        "prefix": prefix,
        "suggestions": [{"term": term, "frequency": freq} for term, freq in suggestions],
    }
    cache.set_json(cache_key, response)
    return {**response, "cache_hit": False}
