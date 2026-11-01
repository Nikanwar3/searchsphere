"""Generate a deterministic synthetic document corpus for benchmarks/demos.

Deterministic means: same output every run, on every machine. We use a
seeded ``random.Random`` instance (never the global ``random`` module) so
the corpus -- and therefore every benchmark number computed from it -- is
reproducible. Word frequencies follow a Zipfian-ish skew (a handful of
topic words repeat often, a long tail appears rarely) because that is how
real text and real query logs actually distribute, and the BM25/top-k
benchmarks are only meaningful against a realistic distribution.

Usage: python scripts/generate_sample_data.py [count] [output_path]
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

TOPICS = {
    "programming": [
        "python", "java", "rust", "compiler", "algorithm", "function", "variable",
        "debugging", "testing", "refactor", "repository", "framework", "database",
        "api", "server", "client", "runtime", "memory", "pointer", "thread",
    ],
    "search_engines": [
        "index", "query", "ranking", "relevance", "crawler", "document", "token",
        "inverted", "trie", "cache", "latency", "throughput", "sharding", "replica",
        "cluster", "pagination", "autocomplete", "ranking", "retrieval", "corpus",
    ],
    "cooking": [
        "recipe", "oven", "bake", "flour", "sugar", "butter", "simmer", "roast",
        "kitchen", "ingredient", "spice", "sauce", "grill", "knife", "pan",
        "chef", "dessert", "breakfast", "dinner", "flavor",
    ],
    "sports": [
        "match", "stadium", "player", "coach", "league", "tournament", "score",
        "team", "referee", "championship", "training", "fitness", "goal",
        "season", "victory", "defense", "offense", "athlete", "record", "medal",
    ],
    "science": [
        "experiment", "hypothesis", "molecule", "gravity", "neuron", "evolution",
        "telescope", "quantum", "chemistry", "physics", "biology", "genome",
        "laboratory", "theory", "particle", "ecosystem", "climate", "energy",
        "reaction", "organism",
    ],
}

COMMON_WORDS = [
    "the", "and", "with", "for", "this", "that", "system", "important",
    "modern", "simple", "complex", "fast", "slow", "large", "small", "new",
]

TITLE_TEMPLATES = [
    "Introduction to {w1} and {w2}",
    "Understanding {w1} in Practice",
    "A Guide to {w1} and {w2}",
    "Advanced {w1} Techniques",
    "{w1} versus {w2}: A Comparison",
    "Why {w1} Matters for {w2}",
    "The Fundamentals of {w1}",
    "{w1}: Lessons Learned",
]


def _generate_body(rng: random.Random, vocab: list[str], length: int) -> str:
    # Zipfian skew: a small "hot" subset of the topic vocabulary is sampled
    # much more often than the rest, mimicking real term-frequency curves.
    hot = vocab[: max(3, len(vocab) // 4)]
    words = []
    for _ in range(length):
        if rng.random() < 0.6:
            words.append(rng.choice(hot))
        elif rng.random() < 0.85:
            words.append(rng.choice(vocab))
        else:
            words.append(rng.choice(COMMON_WORDS))
    return " ".join(words) + "."


def generate_documents(count: int, seed: int = 1337) -> list[dict]:
    rng = random.Random(seed)
    topic_names = list(TOPICS.keys())
    documents = []
    for i in range(count):
        topic = topic_names[i % len(topic_names)]
        vocab = TOPICS[topic]
        w1, w2 = rng.sample(vocab, 2)
        title = rng.choice(TITLE_TEMPLATES).format(w1=w1, w2=w2)
        body_length = rng.randint(40, 160)
        body = _generate_body(rng, vocab, body_length)
        documents.append({"title": title, "body": body})
    return documents


def main() -> None:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data" / "sample_documents.json"

    documents = generate_documents(count)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(documents, indent=2))
    print(f"Wrote {len(documents)} documents to {output_path}")


if __name__ == "__main__":
    main()
