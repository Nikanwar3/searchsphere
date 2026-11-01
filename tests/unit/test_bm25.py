import pytest

from app.core.bm25 import BM25Params, BM25Ranker
from app.core.inverted_index import InvertedIndex


@pytest.fixture
def index():
    idx = InvertedIndex()
    idx.add_document(1, ["python", "python", "python", "tutorial"])
    idx.add_document(2, ["python", "tutorial"])
    idx.add_document(3, ["java", "tutorial"])
    idx.add_document(4, ["cooking", "recipe"])
    return idx


def test_only_matching_documents_are_scored(index):
    ranker = BM25Ranker(index)
    scores = ranker.score_documents(["python"])
    assert set(scores.keys()) == {1, 2}
    assert 3 not in scores
    assert 4 not in scores


def test_higher_term_frequency_scores_higher(index):
    # doc 1 has "python" 3x, doc 2 has it once -> doc 1 should rank higher
    ranker = BM25Ranker(index)
    scores = ranker.score_documents(["python"])
    assert scores[1] > scores[2]


def test_rarer_term_contributes_more_idf(index):
    ranker = BM25Ranker(index)
    # "java" appears in 1/4 docs, "tutorial" in 3/4 docs -> java has higher idf
    assert ranker.idf("java") > ranker.idf("tutorial")


def test_no_query_terms_returns_empty(index):
    ranker = BM25Ranker(index)
    assert ranker.score_documents([]) == {}


def test_empty_index_returns_empty():
    ranker = BM25Ranker(InvertedIndex())
    assert ranker.score_documents(["anything"]) == {}


def test_nonexistent_term_contributes_nothing(index):
    ranker = BM25Ranker(index)
    assert ranker.score_documents(["blockchain"]) == {}


def test_multi_term_query_combines_scores(index):
    ranker = BM25Ranker(index)
    single = ranker.score_documents(["tutorial"])
    combined = ranker.score_documents(["python", "tutorial"])
    # doc 2 matches both terms, so its combined score should exceed its single-term score
    assert combined[2] > single[2]


def test_indexed_scoring_matches_linear_scan_baseline(index):
    ranker = BM25Ranker(index)
    all_ids = [1, 2, 3, 4]
    indexed = ranker.score_documents(["python", "tutorial"])
    linear = ranker.score_documents_linear_scan(["python", "tutorial"], all_ids)
    assert indexed.keys() == linear.keys()
    for doc_id in indexed:
        assert indexed[doc_id] == pytest.approx(linear[doc_id])


def test_custom_k1_b_parameters_change_scores(index):
    default_ranker = BM25Ranker(index)
    aggressive_ranker = BM25Ranker(index, BM25Params(k1=3.0, b=0.0))
    default_scores = default_ranker.score_documents(["python"])
    aggressive_scores = aggressive_ranker.score_documents(["python"])
    assert default_scores != aggressive_scores
