"""Locust load test for the SearchSphere API.

Task weights approximate a realistic search-engine traffic mix: mostly
reads (search, autocomplete), occasional writes (ingestion), rare direct
document fetches.

Run (requires the API to be up and seeded -- see scripts/seed_db.py):
    locust -f benchmarks/locustfile.py --headless -u 50 -r 10 -t 30s \
        --host http://localhost:8000 --csv benchmarks/results/locust
"""
from __future__ import annotations

import random

from locust import HttpUser, between, task

SEARCH_TERMS = [
    "python", "java", "index", "ranking", "recipe", "chef", "stadium",
    "player", "quantum", "chemistry", "algorithm", "database", "cache",
    "trie", "compiler", "experiment",
]
PREFIXES = ["py", "ran", "rec", "sta", "qua", "che", "alg", "dat"]


class SearchSphereUser(HttpUser):
    wait_time = between(0.05, 0.3)

    @task(10)
    def search(self):
        term = random.choice(SEARCH_TERMS)
        offset = random.choice([0, 10, 20])
        self.client.get(f"/search?q={term}&offset={offset}&limit=10", name="/search")

    @task(5)
    def autocomplete(self):
        prefix = random.choice(PREFIXES)
        self.client.get(f"/autocomplete?prefix={prefix}&limit=10", name="/autocomplete")

    @task(2)
    def ingest(self):
        term = random.choice(SEARCH_TERMS)
        payload = {
            "title": f"Load test document about {term}",
            "body": f"{term} appears several times in this generated {term} document about {term}.",
        }
        self.client.post("/documents", json=payload, name="/documents [POST]")

    @task(1)
    def health(self):
        self.client.get("/health", name="/health")
