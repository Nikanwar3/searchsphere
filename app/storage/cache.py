"""Redis-backed result cache with O(1) bulk invalidation.

Rather than deleting potentially thousands of cached search/autocomplete
keys whenever a document is ingested or removed (which would require a
SCAN + DEL pass, racy under concurrent writers and slow at scale), every
cache key embeds a monotonically increasing "index version" fetched from
Redis. Mutating the index bumps the version with ``INCR`` -- a single
atomic O(1) operation -- which makes every previously-cached key's version
segment stale. Old keys are simply never looked up again and expire on
their own TTL; no explicit deletion is required, and the scheme is safe
under concurrent ingests because ``INCR`` is atomic at the Redis level.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

import redis

from app.config import get_settings

_VERSION_KEY = "searchsphere:index_version"


def get_redis_client() -> redis.Redis:
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


class ResultCache:
    def __init__(self, client: redis.Redis, ttl_seconds: int) -> None:
        self._client = client
        self._ttl = ttl_seconds

    def current_version(self) -> int:
        value = self._client.get(_VERSION_KEY)
        return int(value) if value is not None else 0

    def invalidate(self) -> int:
        """Bump the index version. O(1), atomic, safe under concurrency."""
        return self._client.incr(_VERSION_KEY)

    def _key(self, namespace: str, payload: str) -> str:
        version = self.current_version()
        digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:20]
        return f"searchsphere:{namespace}:v{version}:{digest}"

    def search_key(self, query: str, offset: int, limit: int) -> str:
        return self._key("search", f"{query}|{offset}|{limit}")

    def autocomplete_key(self, prefix: str, limit: int) -> str:
        return self._key("autocomplete", f"{prefix}|{limit}")

    def get_json(self, key: str) -> Optional[Any]:
        raw = self._client.get(key)
        return json.loads(raw) if raw is not None else None

    def set_json(self, key: str, value: Any) -> None:
        self._client.set(key, json.dumps(value), ex=self._ttl)
