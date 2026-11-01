"""FastAPI dependency providers.

The Redis client and ``ResultCache`` are created once per process (not per
request) since ``redis-py`` clients are connection-pooled and thread-safe;
recreating them per request would discard that pooling for no benefit.
"""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.services.index_manager import IndexManager, get_index_manager
from app.storage.cache import ResultCache, get_redis_client

__all__ = ["get_db", "index_manager_dependency", "cache_dependency"]

from app.storage.db import get_db  # re-exported for a single import surface


@lru_cache
def _cache_singleton() -> ResultCache:
    settings = get_settings()
    return ResultCache(get_redis_client(), ttl_seconds=settings.cache_ttl_seconds)


def index_manager_dependency() -> IndexManager:
    return get_index_manager()


def cache_dependency() -> ResultCache:
    return _cache_singleton()
