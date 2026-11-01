import random

import pytest

from app.core.topk import (
    paginate_top_k,
    top_k_bounded_heap,
    top_k_full_sort,
    top_k_heapq_nlargest,
)

IMPLEMENTATIONS = [top_k_full_sort, top_k_heapq_nlargest, top_k_bounded_heap]


@pytest.fixture
def scores():
    return {1: 3.0, 2: 9.5, 3: 1.2, 4: 9.5, 5: 7.0}


@pytest.mark.parametrize("impl", IMPLEMENTATIONS)
def test_returns_correct_top_k(impl, scores):
    # 4 and 2 tie at 9.5; tie-break is ascending doc_id -> 2 before 4
    assert impl(scores, 3) == [(2, 9.5), (4, 9.5), (5, 7.0)]


@pytest.mark.parametrize("impl", IMPLEMENTATIONS)
def test_k_larger_than_input_returns_everything(impl, scores):
    assert len(impl(scores, 100)) == len(scores)


@pytest.mark.parametrize("impl", IMPLEMENTATIONS)
def test_k_zero_returns_empty(impl, scores):
    assert impl(scores, 0) == []


@pytest.mark.parametrize("impl", IMPLEMENTATIONS)
def test_empty_scores_returns_empty(impl):
    assert impl({}, 5) == []


@pytest.mark.parametrize("impl", IMPLEMENTATIONS)
def test_all_implementations_agree_on_random_input(impl):
    rng = random.Random(42)
    scores = {doc_id: rng.random() for doc_id in range(500)}
    expected = top_k_full_sort(scores, 10)
    assert impl(scores, 10) == expected


def test_paginate_top_k_pages_through_results():
    scores = {i: float(100 - i) for i in range(50)}  # doc 0 has the highest score
    page1, total = paginate_top_k(scores, offset=0, limit=10)
    page2, total2 = paginate_top_k(scores, offset=10, limit=10)
    assert total == total2 == 50
    assert [doc_id for doc_id, _ in page1] == list(range(0, 10))
    assert [doc_id for doc_id, _ in page2] == list(range(10, 20))


def test_paginate_top_k_offset_beyond_total_returns_empty():
    scores = {1: 1.0, 2: 2.0}
    page, total = paginate_top_k(scores, offset=10, limit=5)
    assert page == []
    assert total == 2


@pytest.mark.parametrize("impl", IMPLEMENTATIONS)
def test_tied_scores_select_a_k_independent_prefix(impl):
    # Regression test: all 15 docs tie at the same score. The set of items
    # chosen for a smaller k must be a strict prefix (by doc_id ascending)
    # of the set chosen for a larger k -- otherwise paginating through tied
    # results (see test_api_search.test_pagination_offset_and_limit) skips
    # or repeats rows depending on page size.
    scores = {doc_id: 1.0 for doc_id in range(1, 16)}
    top5 = [doc_id for doc_id, _ in impl(scores, 5)]
    top10 = [doc_id for doc_id, _ in impl(scores, 10)]
    assert top5 == list(range(1, 6))
    assert top10 == list(range(1, 11))
    assert top10[:5] == top5


def test_paginate_top_k_zero_limit():
    scores = {1: 1.0}
    page, total = paginate_top_k(scores, offset=0, limit=0)
    assert page == []
    assert total == 1
