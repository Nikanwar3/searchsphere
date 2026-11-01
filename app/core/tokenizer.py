"""Deterministic text tokenization shared by indexing and query processing.

Using the same tokenizer for documents and queries is required for the
inverted index and BM25 ranker to agree on vocabulary.
"""
from __future__ import annotations

import re
from typing import List

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")

# A small, fixed stopword list. Kept intentionally short: aggressive stopword
# removal can hurt recall on short queries (e.g. "to be or not to be"), and a
# search engine demo should favor predictable behavior over cleverness.
STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "is", "are", "was", "were",
        "in", "on", "at", "of", "to", "for", "with", "by", "it", "this",
        "that", "as", "be", "from",
    }
)


def tokenize(text: str, *, remove_stopwords: bool = True) -> List[str]:
    """Split ``text`` into lowercase alphanumeric tokens.

    Time: O(n) in the length of ``text`` (single regex scan).
    Space: O(t) for the t tokens produced.
    """
    if not text:
        return []
    tokens = _TOKEN_RE.findall(text.lower())
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    return tokens
