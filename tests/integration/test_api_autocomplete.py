def _ingest(client, title, body):
    client.post("/documents", json={"title": title, "body": body})


def test_autocomplete_returns_prefix_matches(client):
    _ingest(client, "doc1", "python programming")
    _ingest(client, "doc2", "programming languages")

    resp = client.get("/autocomplete", params={"prefix": "prog"})
    assert resp.status_code == 200
    terms = {s["term"] for s in resp.json()["suggestions"]}
    assert terms == {"programming"}


def test_autocomplete_ranked_by_document_frequency(client):
    # Popularity is "how many documents contain this term", not raw term
    # frequency within one document -- "apple" appears in 3 separate
    # documents, so it should outrank terms that each appear in only one.
    _ingest(client, "doc1", "apple")
    _ingest(client, "doc2", "apple")
    _ingest(client, "doc3", "apple")
    _ingest(client, "doc4", "application")
    _ingest(client, "doc5", "app")

    resp = client.get("/autocomplete", params={"prefix": "app"})
    terms = [s["term"] for s in resp.json()["suggestions"]]
    assert terms[0] == "apple"


def test_autocomplete_no_matches(client):
    _ingest(client, "doc1", "hello world")
    resp = client.get("/autocomplete", params={"prefix": "zzz"})
    assert resp.status_code == 200
    assert resp.json()["suggestions"] == []


def test_autocomplete_empty_prefix_rejected(client):
    resp = client.get("/autocomplete", params={"prefix": ""})
    assert resp.status_code == 422


def test_autocomplete_limit_respected(client):
    for word in ["cat1", "cat2", "cat3", "cat4"]:
        _ingest(client, word, word)

    resp = client.get("/autocomplete", params={"prefix": "cat", "limit": 2})
    assert len(resp.json()["suggestions"]) == 2


def test_autocomplete_against_empty_index(client):
    resp = client.get("/autocomplete", params={"prefix": "any"})
    assert resp.json()["suggestions"] == []


def test_autocomplete_removed_after_document_deletion(client):
    created = _ingest_and_get_id("uniqueword document", client)
    assert client.get("/autocomplete", params={"prefix": "uniquew"}).json()["suggestions"]

    client.delete(f"/documents/{created}")

    assert client.get("/autocomplete", params={"prefix": "uniquew"}).json()["suggestions"] == []


def _ingest_and_get_id(body, client):
    resp = client.post("/documents", json={"title": "doc", "body": body})
    return resp.json()["doc_id"]
