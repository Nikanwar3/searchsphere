def _ingest(client, title, body):
    return client.post("/documents", json={"title": title, "body": body}).json()["doc_id"]


def test_search_returns_matching_documents(client):
    _ingest(client, "Python Tutorial", "Learn Python programming from scratch.")
    _ingest(client, "Cooking Recipes", "How to bake a cake.")

    resp = client.get("/search", params={"q": "python"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["results"]) == 1
    assert body["results"][0]["title"] == "Python Tutorial"


def test_search_ranks_higher_term_frequency_first(client):
    _ingest(client, "Doc A", "python python python programming")
    _ingest(client, "Doc B", "python programming")

    resp = client.get("/search", params={"q": "python"})
    titles = [r["title"] for r in resp.json()["results"]]
    assert titles == ["Doc A", "Doc B"]


def test_search_no_matches_returns_empty_results(client):
    _ingest(client, "Doc A", "completely unrelated content")

    resp = client.get("/search", params={"q": "blockchain"})
    assert resp.status_code == 200
    assert resp.json() == {
        "query": "blockchain",
        "total": 0,
        "offset": 0,
        "limit": 10,
        "cache_hit": False,
        "results": [],
    }


def test_empty_query_rejected(client):
    resp = client.get("/search", params={"q": ""})
    assert resp.status_code == 422


def test_whitespace_only_query_rejected(client):
    resp = client.get("/search", params={"q": "   "})
    assert resp.status_code == 422


def test_search_against_empty_corpus(client):
    resp = client.get("/search", params={"q": "anything"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_pagination_offset_and_limit(client):
    for i in range(15):
        _ingest(client, f"Doc {i}", "shared searchable keyword content")

    page1 = client.get("/search", params={"q": "shared", "offset": 0, "limit": 5}).json()
    page2 = client.get("/search", params={"q": "shared", "offset": 5, "limit": 5}).json()

    assert page1["total"] == 15
    assert len(page1["results"]) == 5
    assert len(page2["results"]) == 5
    ids_page1 = {r["doc_id"] for r in page1["results"]}
    ids_page2 = {r["doc_id"] for r in page2["results"]}
    assert ids_page1.isdisjoint(ids_page2)


def test_limit_upper_bound_enforced(client):
    resp = client.get("/search", params={"q": "x", "limit": 1000})
    assert resp.status_code == 422


def test_negative_offset_rejected(client):
    resp = client.get("/search", params={"q": "x", "offset": -1})
    assert resp.status_code == 422


def test_query_of_only_stopwords_returns_empty_gracefully(client):
    _ingest(client, "Doc A", "the cat sat on the mat")
    resp = client.get("/search", params={"q": "the and or"})
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_deleted_document_no_longer_appears_in_search(client):
    doc_id = _ingest(client, "Temp Doc", "ephemeral searchable term")
    assert client.get("/search", params={"q": "ephemeral"}).json()["total"] == 1

    client.delete(f"/documents/{doc_id}")

    assert client.get("/search", params={"q": "ephemeral"}).json()["total"] == 0
