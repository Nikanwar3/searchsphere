"""Indexed BM25 search vs. a linear-scan baseline, at several corpus sizes.

Both code paths compute the identical BM25 score (see
app/core/bm25.py:score_documents vs score_documents_linear_scan); the only
difference is whether scoring touches only documents containing a query
term (indexed) or every document in the corpus (linear scan). This isolates
the complexity win of the inverted index -- O(sum of df(term)) vs O(N*|Q|)
-- from any BM25-specific effect.

Run: python benchmarks/bench_search_vs_linear.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.bm25 import BM25Ranker  # noqa: E402
from app.core.inverted_index import InvertedIndex  # noqa: E402
from app.core.tokenizer import tokenize  # noqa: E402
from benchmarks._utils import compute_stats, time_calls  # noqa: E402

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_documents.json"
CORPUS_SIZES = [100, 500, 1000, 2000]
QUERIES = [
    "python",          # single, moderately common term
    "index ranking",   # two moderately common terms
    "quantum",         # single, rarer term
]
REPEATS = 200
PROCESS = psutil.Process()


def build_index(documents: list[dict]) -> tuple[InvertedIndex, list[int]]:
    index = InvertedIndex()
    for doc_id, doc in enumerate(documents, start=1):
        tokens = tokenize(f"{doc['title']} {doc['body']}")
        index.add_document(doc_id, tokens)
    return index, [doc_id for doc_id in range(1, len(documents) + 1)]


def run() -> dict:
    all_documents = json.loads(DATA_PATH.read_text())
    results = {"corpus_sizes": {}}

    for size in CORPUS_SIZES:
        documents = all_documents[:size]

        PROCESS.memory_info()  # warm up the measurement
        rss_before = PROCESS.memory_info().rss
        index, all_ids = build_index(documents)
        rss_after = PROCESS.memory_info().rss
        ranker = BM25Ranker(index)

        query_results = {}
        for query in QUERIES:
            terms = tokenize(query)
            if not terms:
                continue
            indexed_latencies = time_calls(lambda: ranker.score_documents(terms), REPEATS)
            linear_latencies = time_calls(
                lambda: ranker.score_documents_linear_scan(terms, all_ids), REPEATS
            )
            indexed_stats = compute_stats(indexed_latencies)
            linear_stats = compute_stats(linear_latencies)
            query_results[query] = {
                "indexed": indexed_stats.as_dict(),
                "linear_scan": linear_stats.as_dict(),
                "speedup_x": round(linear_stats.mean_ms / indexed_stats.mean_ms, 2)
                if indexed_stats.mean_ms > 0
                else None,
                "matching_documents": len(index.candidate_documents(terms)),
            }

        results["corpus_sizes"][size] = {
            "index_memory_delta_mb": round((rss_after - rss_before) / (1024 * 1024), 3),
            "queries": query_results,
        }

    return results


def print_report(results: dict) -> None:
    print(f"{'corpus':>8} {'query':<22} {'matches':>8} {'indexed p95 (ms)':>18} "
          f"{'linear p95 (ms)':>18} {'speedup':>9}")
    for size, data in results["corpus_sizes"].items():
        for query, q in data["queries"].items():
            print(f"{size:>8} {query:<22} {q['matching_documents']:>8} "
                  f"{q['indexed']['p95_ms']:>18.4f} {q['linear_scan']['p95_ms']:>18.4f} "
                  f"{q['speedup_x']:>8.2f}x")
        print(f"{'':>8} index memory for {size} docs: {data['index_memory_delta_mb']} MB")


if __name__ == "__main__":
    results = run()
    print_report(results)
    out_path = Path(__file__).resolve().parent / "results" / "search_vs_linear.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nFull results written to {out_path}")
