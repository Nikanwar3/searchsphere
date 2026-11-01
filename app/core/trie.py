"""A frequency-weighted Trie for prefix autocomplete.

Each node holds a dict of children keyed by character and, for nodes that
terminate a word, the word's popularity (how many times it has been
inserted/queried for -- here, how many documents contained it). Suggestions
for a prefix are ranked by popularity so common terms surface first, which
is how real autocomplete behaves (rather than alphabetically).
"""
from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple


class _TrieNode:
    __slots__ = ("children", "is_word", "frequency")

    def __init__(self) -> None:
        self.children: Dict[str, "_TrieNode"] = {}
        self.is_word: bool = False
        self.frequency: int = 0


class Trie:
    def __init__(self) -> None:
        self._root = _TrieNode()
        self._size = 0  # distinct words stored

    def insert(self, word: str, weight: int = 1) -> None:
        """Insert ``word`` (or bump its frequency by ``weight`` if present).

        Time: O(L) in the length of the word -- one hop per character.
        Space: O(L) worst case for new nodes.
        """
        if not word:
            return
        node = self._root
        for ch in word:
            child = node.children.get(ch)
            if child is None:
                child = _TrieNode()
                node.children[ch] = child
            node = child
        if not node.is_word:
            self._size += 1
        node.is_word = True
        node.frequency += weight

    def remove_weight(self, word: str, weight: int = 1) -> None:
        """Decrement a word's frequency (used when a document is deleted).

        The word is only actually unlinked from the trie (is_word cleared)
        once its frequency drops to zero, so a term shared by several
        documents stays suggestible until the last document is removed.
        Time: O(L).
        """
        node = self._find_node(word)
        if node is None or not node.is_word:
            return
        node.frequency = max(0, node.frequency - weight)
        if node.frequency == 0:
            node.is_word = False
            self._size -= 1

    def _find_node(self, prefix: str) -> Optional[_TrieNode]:
        node = self._root
        for ch in prefix:
            node = node.children.get(ch)
            if node is None:
                return None
        return node

    def search_exact(self, word: str) -> bool:
        node = self._find_node(word)
        return bool(node and node.is_word)

    def suggest(self, prefix: str, limit: int = 10) -> List[Tuple[str, int]]:
        """Top ``limit`` words starting with ``prefix``, ranked by frequency
        (ties broken lexicographically).

        Time: O(P + M log limit) where P is len(prefix) (trie descent) and
        M is the number of words in the prefix's subtree -- we DFS the
        subtree once, O(M), and maintain a bounded min-heap of size
        ``limit`` (see app.core.topk for the same pattern) rather than
        collecting and sorting all M matches, which would cost
        O(M log M) and defeats the point when a short, popular prefix
        (e.g. "a") matches a huge subtree but the caller only wants 10
        results.
        Space: O(limit) for the heap + O(P) recursion depth.
        """
        if limit <= 0:
            return []
        start = self._find_node(prefix)
        if start is None:
            return []

        heap: List[Tuple[int, str]] = []  # min-heap on (frequency, negated-lexical-key)

        def visit(node: _TrieNode, word: str) -> None:
            if node.is_word:
                # Store (-frequency is NOT used here; we keep raw frequency and
                # break ties with word itself, inverted for max-heap-by-min-heap trick)
                entry = (node.frequency, word)
                if len(heap) < limit:
                    heapq.heappush(heap, entry)
                elif entry > heap[0]:
                    heapq.heapreplace(heap, entry)
            for ch, child in node.children.items():
                visit(child, word + ch)

        visit(start, prefix)
        # Highest frequency first; lexicographic ascending for ties.
        return sorted(((w, f) for f, w in heap), key=lambda wf: (-wf[1], wf[0]))

    @property
    def size(self) -> int:
        return self._size
