"""Cache-correctness tests: a cached response must never outlive the data
it was computed from.
"""


def test_second_identical_search_is_a_cache_hit(client):
    client.post("/documents", json={"title": "Doc", "body": "cacheable keyword"})

    first = client.get("/search", params={"q": "cacheable"}).json()
    second = client.get("/search", params={"q": "cacheable"}).json()

    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert first["results"] == second["results"]


def test_ingesting_a_document_invalidates_search_cache(client):
    client.get("/search", params={"q": "freshterm"})  # warm the (empty) cache

    client.post("/documents", json={"title": "New Doc", "body": "freshterm appears here"})

    resp = client.get("/search", params={"q": "freshterm"}).json()
    assert resp["cache_hit"] is False  # version bumped -> old cached empty result is unreachable
    assert resp["total"] == 1


def test_deleting_a_document_invalidates_search_cache(client):
    doc_id = client.post(
        "/documents", json={"title": "Doc", "body": "willbedeleted term"}
    ).json()["doc_id"]
    client.get("/search", params={"q": "willbedeleted"})  # warm cache with a hit

    client.delete(f"/documents/{doc_id}")

    resp = client.get("/search", params={"q": "willbedeleted"}).json()
    assert resp["cache_hit"] is False
    assert resp["total"] == 0


def test_ingestion_invalidates_autocomplete_cache(client):
    client.get("/autocomplete", params={"prefix": "newwo"})  # warm empty cache

    client.post("/documents", json={"title": "Doc", "body": "newword appears"})

    resp = client.get("/autocomplete", params={"prefix": "newwo"}).json()
    assert resp["cache_hit"] is False
    assert any(s["term"] == "newword" for s in resp["suggestions"])


def test_duplicate_ingestion_does_not_invalidate_cache(client):
    payload = {"title": "Doc", "body": "stable content here"}
    client.post("/documents", json=payload)

    client.get("/search", params={"q": "stable"})  # cache miss, now cached
    client.post("/documents", json=payload)  # duplicate -> should NOT bump version
    second = client.get("/search", params={"q": "stable"}).json()

    assert second["cache_hit"] is True
