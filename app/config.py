"""Centralized, environment-driven configuration.

All runtime knobs (DB/Redis connection info, BM25 parameters, pagination
limits) live here so there is exactly one place to look, and so tests can
override settings via environment variables without touching code.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://searchsphere:searchsphere@localhost:5432/searchsphere"
    redis_url: str = "redis://localhost:6379/3"
    cache_ttl_seconds: int = 60

    bm25_k1: float = 1.5
    bm25_b: float = 0.75

    api_title: str = "SearchSphere"
    api_default_page_size: int = 10
    api_max_page_size: int = 100
    autocomplete_max_suggestions: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
