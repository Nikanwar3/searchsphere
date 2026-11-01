"""Cached vs. uncached search latency against a *running* SearchSphere
server (real HTTP, real Postgres, real Redis -- not an in-process shortcut).

Each query is sent once to force a cache miss (bumping to a query string
that has never been seen, so there is no possibility of a stale hit), timed,
then sent again N times to measure cache-hit latency.

Prerequisite: the API must be running and reachable at --host, and the
database should already contain documents (see scripts/seed_db.py).

Run: python benchmarks/bench_cache.py --host http://localhost:8000
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks._utils import compute_stats, time_calls  # noqa: E402

QUERIES = ["python", "ranking index", "quantum", "chef recipe", "stadium championship"]
REPEATS = 100


def run(host: str) -> dict:
    client = httpx.Client(base_url=host, timeout=10.0)
    results = {}

    for query in QUERIES:
        # Each "uncached" sample must be a genuine cache miss, so every repeat
        # uses a distinct cache-busted query string rather than repeating one.
        uncached_latencies = []
        for i in range(REPEATS):
            latencies = time_calls(
                lambda i=i: client.get("/search", params={"q": f"{query} bust{i}", "limit": 10}), 1
            )
            uncached_latencies.extend(latencies)

        # Warm the cache once for the plain query, then measure pure cache hits.
        client.get("/search", params={"q": query, "limit": 10})
        cached_latencies = time_calls(lambda: client.get("/search", params={"q": query, "limit": 10}), REPEATS)

        uncached_stats = compute_stats(uncached_latencies)
        cached_stats = compute_stats(cached_latencies)
        results[query] = {
            "uncached": uncached_stats.as_dict(),
            "cached": cached_stats.as_dict(),
            "speedup_x": round(uncached_stats.mean_ms / cached_stats.mean_ms, 2)
            if cached_stats.mean_ms > 0
            else None,
        }

    client.close()
    return results


def print_report(results: dict) -> None:
    print(f"{'query':<24} {'uncached p95 (ms)':>18} {'cached p95 (ms)':>16} {'speedup':>9}")
    for query, r in results.items():
        print(f"{query:<24} {r['uncached']['p95_ms']:>18.4f} {r['cached']['p95_ms']:>16.4f} "
              f"{r['speedup_x']:>8.2f}x")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8000")
    args = parser.parse_args()

    results = run(args.host)
    print_report(results)
    out_path = Path(__file__).resolve().parent / "results" / "cache_comparison.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nFull results written to {out_path}")
