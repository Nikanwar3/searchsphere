"""Compare the three Top-K selection strategies (app/core/topk.py) across
corpus sizes (n) and page sizes (k).

Expectation per the documented complexity: top_k_full_sort (O(n log n)) is
fastest only when k approaches n; top_k_bounded_heap (O(n log k), O(k)
space) should win as n grows large and k stays small -- the realistic
"search result page" shape.

Run: python benchmarks/bench_topk.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.topk import (  # noqa: E402
    top_k_bounded_heap,
    top_k_full_sort,
    top_k_heapq_nlargest,
)
from benchmarks._utils import compute_stats, time_calls  # noqa: E402

N_VALUES = [1_000, 10_000, 100_000]
K_VALUES = [10, 50, 500]
REPEATS = 50

IMPLEMENTATIONS = {
    "full_sort": top_k_full_sort,
    "heapq_nlargest": top_k_heapq_nlargest,
    "bounded_heap": top_k_bounded_heap,
}


def make_scores(n: int, seed: int = 7) -> dict:
    rng = random.Random(seed)
    return {doc_id: rng.random() for doc_id in range(n)}


def run() -> dict:
    results = {}
    for n in N_VALUES:
        scores = make_scores(n)
        results[n] = {}
        for k in K_VALUES:
            if k > n:
                continue
            results[n][k] = {}
            for name, fn in IMPLEMENTATIONS.items():
                latencies = time_calls(lambda: fn(scores, k), REPEATS)
                results[n][k][name] = compute_stats(latencies).as_dict()
    return results


def print_report(results: dict) -> None:
    print(f"{'n':>8} {'k':>6} {'full_sort p95':>15} {'heapq_nlargest p95':>20} {'bounded_heap p95':>18}")
    for n, by_k in results.items():
        for k, by_impl in by_k.items():
            print(f"{n:>8} {k:>6} "
                  f"{by_impl['full_sort']['p95_ms']:>15.4f} "
                  f"{by_impl['heapq_nlargest']['p95_ms']:>20.4f} "
                  f"{by_impl['bounded_heap']['p95_ms']:>18.4f}")


if __name__ == "__main__":
    results = run()
    print_report(results)
    out_path = Path(__file__).resolve().parent / "results" / "topk_comparison.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nFull results written to {out_path}")
