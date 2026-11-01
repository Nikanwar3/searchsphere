from app.core.tokenizer import tokenize


def test_basic_tokenization():
    assert tokenize("Hello, World!") == ["hello", "world"]


def test_stopwords_removed_by_default():
    assert tokenize("the cat and the hat") == ["cat", "hat"]


def test_stopwords_kept_when_disabled():
    assert tokenize("the cat", remove_stopwords=False) == ["the", "cat"]


def test_empty_string():
    assert tokenize("") == []


def test_whitespace_only():
    assert tokenize("   \n\t  ") == []


def test_numbers_and_apostrophes():
    assert tokenize("Python 3.13 isn't slow") == ["python", "3", "13", "isn't", "slow"]


def test_case_insensitivity():
    assert tokenize("Search SEARCH search") == ["search", "search", "search"]
