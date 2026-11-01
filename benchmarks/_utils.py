"""Shared helpers for the benchmark scripts: percentile math and a tiny
stopwatch, nothing fancy. No external stats dependency needed for p50/p95.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable, List


@dataclass
class LatencyStats:
    count: int
    mean_ms: float
    median_ms: float
    p95_ms: float
    min_ms: float
    max_ms: float

    def as_dict(self) -> dict:
        return {
            "count": self.count,
            "mean_ms": round(self.mean_ms, 4),
            "median_ms": round(self.median_ms, 4),
            "p95_ms": round(self.p95_ms, 4),
            "min_ms": round(self.min_ms, 4),
            "max_ms": round(self.max_ms, 4),
        }


def _percentile(sorted_values: List[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def compute_stats(latencies_s: List[float]) -> LatencyStats:
    values_ms = sorted(v * 1000 for v in latencies_s)
    return LatencyStats(
        count=len(values_ms),
        mean_ms=sum(values_ms) / len(values_ms),
        median_ms=_percentile(values_ms, 50),
        p95_ms=_percentile(values_ms, 95),
        min_ms=values_ms[0],
        max_ms=values_ms[-1],
    )


def time_calls(fn: Callable[[], object], repeats: int) -> List[float]:
    latencies = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        latencies.append(time.perf_counter() - start)
    return latencies
