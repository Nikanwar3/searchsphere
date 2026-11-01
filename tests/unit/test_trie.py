from app.core.trie import Trie


def test_insert_and_search_exact():
    trie = Trie()
    trie.insert("search")
    assert trie.search_exact("search") is True
    assert trie.search_exact("sear") is False


def test_suggest_prefix_matches():
    trie = Trie()
    for word in ["cat", "car", "cart", "dog"]:
        trie.insert(word)
    suggestions = {term for term, _ in trie.suggest("ca")}
    assert suggestions == {"cat", "car", "cart"}


def test_suggest_ranked_by_frequency():
    trie = Trie()
    trie.insert("apple", weight=5)
    trie.insert("app", weight=1)
    trie.insert("application", weight=10)
    results = trie.suggest("app", limit=3)
    assert [term for term, _ in results] == ["application", "apple", "app"]


def test_suggest_respects_limit():
    trie = Trie()
    for word in ["a1", "a2", "a3", "a4", "a5"]:
        trie.insert(word)
    assert len(trie.suggest("a", limit=2)) == 2


def test_suggest_ties_broken_lexicographically():
    trie = Trie()
    trie.insert("zebra", weight=1)
    trie.insert("apple", weight=1)
    results = trie.suggest("", limit=2)
    assert [term for term, _ in results] == ["apple", "zebra"]


def test_suggest_no_match_returns_empty():
    trie = Trie()
    trie.insert("hello")
    assert trie.suggest("xyz") == []


def test_suggest_empty_trie():
    trie = Trie()
    assert trie.suggest("a") == []


def test_repeated_insert_increments_frequency():
    trie = Trie()
    trie.insert("python")
    trie.insert("python")
    results = trie.suggest("py")
    assert results == [("python", 2)]
    assert trie.size == 1


def test_remove_weight_fully_unlinks_word_at_zero():
    trie = Trie()
    trie.insert("python", weight=2)
    trie.remove_weight("python", weight=2)
    assert trie.search_exact("python") is False
    assert trie.suggest("py") == []
    assert trie.size == 0


def test_remove_weight_partial_keeps_word_suggestible():
    trie = Trie()
    trie.insert("python", weight=2)
    trie.remove_weight("python", weight=1)
    assert trie.search_exact("python") is True
    assert trie.suggest("py") == [("python", 1)]


def test_remove_weight_nonexistent_word_is_noop():
    trie = Trie()
    trie.remove_weight("ghost")  # should not raise
    assert trie.size == 0
