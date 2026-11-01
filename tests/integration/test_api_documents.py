def test_ingest_and_fetch_document(client):
    resp = client.post("/documents", json={"title": "Intro to Python", "body": "Python is a language."})
    assert resp.status_code == 201
    body = resp.json()
    assert body["created"] is True
    doc_id = body["doc_id"]

    fetched = client.get(f"/documents/{doc_id}")
    assert fetched.status_code == 200
    assert fetched.json() == {"doc_id": doc_id, "title": "Intro to Python", "body": "Python is a language."}


def test_get_nonexistent_document_returns_404(client):
    resp = client.get("/documents/999999")
    assert resp.status_code == 404


def test_blank_title_rejected(client):
    resp = client.post("/documents", json={"title": "   ", "body": "valid body"})
    assert resp.status_code == 422


def test_blank_body_rejected(client):
    resp = client.post("/documents", json={"title": "valid title", "body": ""})
    assert resp.status_code == 422


def test_missing_fields_rejected(client):
    resp = client.post("/documents", json={"title": "only title"})
    assert resp.status_code == 422


def test_duplicate_document_is_idempotent(client):
    payload = {"title": "Same Doc", "body": "Identical content every time."}
    first = client.post("/documents", json=payload)
    second = client.post("/documents", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert first.json()["doc_id"] == second.json()["doc_id"]


def test_duplicate_detection_ignores_case_and_surrounding_whitespace(client):
    client.post("/documents", json={"title": "Case Test", "body": "Some Body Text"})
    dup = client.post("/documents", json={"title": "  case test  ", "body": "  some body text  "})
    assert dup.json()["created"] is False


def test_delete_document(client):
    created = client.post("/documents", json={"title": "To Delete", "body": "ephemeral"}).json()
    doc_id = created["doc_id"]

    deleted = client.delete(f"/documents/{doc_id}")
    assert deleted.status_code == 204

    assert client.get(f"/documents/{doc_id}").status_code == 404


def test_delete_nonexistent_document_returns_404(client):
    resp = client.delete("/documents/999999")
    assert resp.status_code == 404


def test_deleting_a_document_frees_its_content_hash_for_reuse(client):
    payload = {"title": "Reusable", "body": "content"}
    first = client.post("/documents", json=payload).json()
    client.delete(f"/documents/{first['doc_id']}")

    second = client.post("/documents", json=payload)
    assert second.status_code == 201
    assert second.json()["created"] is True
    assert second.json()["doc_id"] != first["doc_id"]
