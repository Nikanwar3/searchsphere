import pytest

from app.core.inverted_index import InvertedIndex


@pytest.fixture
def index():
    idx = InvertedIndex()
    idx.add_document(1, ["python", "is", "great", "python"])
    idx.add_document(2, ["java", "is", "verbose"])
    idx.add_document(3, ["python", "and", "java", "are", "popular"])
    return idx


def test_document_count(index):
    assert index.document_count == 3


def test_postings_term_frequency(index):
    postings = index.get_postings("python")
    assert postings == {1: 2, 3: 1}


def test_document_frequency(index):
    assert index.document_frequency("python") == 2
    assert index.document_frequency("verbose") == 1
    assert index.document_frequency("nonexistent") == 0


def test_document_length(index):
    assert index.document_length(1) == 4
    assert index.document_length(2) == 3


def test_average_document_length(index):
    # doc lengths: 4, 3, 5 -> avg = 4.0
    assert index.average_document_length == pytest.approx(4.0)


def test_candidate_documents_union(index):
    assert index.candidate_documents(["python", "verbose"]) == {1, 2, 3}
    assert index.candidate_documents(["nonexistent"]) == set()


def test_remove_document_cleans_postings(index):
    assert index.remove_document(1) is True
    assert index.document_count == 2
    assert index.get_postings("python") == {3: 1}
    assert index.document_length(1) == 0
    assert not index.contains(1)


def test_remove_document_deletes_empty_term_entries():
    idx = InvertedIndex()
    idx.add_document(1, ["unique_term"])
    assert "unique_term" in idx.vocabulary()
    idx.remove_document(1)
    assert "unique_term" not in idx.vocabulary()


def test_remove_nonexistent_document_returns_false(index):
    assert index.remove_document(999) is False


def test_reindexing_same_doc_id_replaces_content():
    idx = InvertedIndex()
    idx.add_document(1, ["alpha", "beta"])
    idx.add_document(1, ["gamma"])  # re-index under the same id
    assert idx.document_count == 1
    assert idx.get_postings("alpha") == {}
    assert idx.get_postings("gamma") == {1: 1}


def test_empty_index_has_zero_average_length():
    idx = InvertedIndex()
    assert idx.average_document_length == 0.0
    assert idx.document_count == 0


def test_empty_document_tokens():
    idx = InvertedIndex()
    idx.add_document(1, [])
    assert idx.document_count == 1
    assert idx.document_length(1) == 0
