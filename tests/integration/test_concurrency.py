"""Concurrency safety: the duplicate-content race and the shared in-memory
index must both behave correctly under simultaneous requests.
"""
from concurrent.futures import ThreadPoolExecutor


def test_concurrent_duplicate_ingestion_creates_exactly_one_document(client):
    payload = {"title": "Race Doc", "body": "identical racing content"}

    with ThreadPoolExecutor(max_workers=10) as pool:
        responses = list(pool.map(lambda _: client.post("/documents", json=payload), range(10)))

    doc_ids = {r.json()["doc_id"] for r in responses}
    created_flags = [r.json()["created"] for r in responses]

    assert all(r.status_code == 201 for r in responses)
    assert len(doc_ids) == 1, "all concurrent duplicate posts must resolve to the same document"
    assert created_flags.count(True) == 1
    assert created_flags.count(False) == 9


def test_concurrent_distinct_ingestions_all_persist_and_index(client):
    def ingest(i: int):
        return client.post("/documents", json={"title": f"Doc {i}", "body": f"unique content number {i}"})

    with ThreadPoolExecutor(max_workers=10) as pool:
        responses = list(pool.map(ingest, range(20)))

    assert all(r.status_code == 201 for r in responses)
    doc_ids = {r.json()["doc_id"] for r in responses}
    assert len(doc_ids) == 20

    health = client.get("/health").json()
    assert health["indexed_documents"] == 20


def test_concurrent_reads_and_writes_do_not_error(client):
    client.post("/documents", json={"title": "Seed", "body": "stable searchable term"})

    def write(i: int):
        return client.post("/documents", json={"title": f"W{i}", "body": f"stable term {i}"})

    def read(_i: int):
        return client.get("/search", params={"q": "stable"})

    with ThreadPoolExecutor(max_workers=16) as pool:
        writes = pool.map(write, range(8))
        reads = pool.map(read, range(8))
        all_responses = list(writes) + list(reads)

    assert all(r.status_code < 500 for r in all_responses)
