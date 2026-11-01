"""Load data/sample_documents.json into PostgreSQL via the real repository
layer (so content-hash dedup logic and timestamps behave exactly as they
would in production). Used to prime a database before running benchmarks
or Locust load tests.

Usage: python scripts/seed_db.py [--reset] [path/to/documents.json]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.storage import repository  # noqa: E402
from app.storage.db import Base, SessionLocal, engine  # noqa: E402


def main() -> None:
    args = sys.argv[1:]
    reset = "--reset" in args
    args = [a for a in args if a != "--reset"]
    data_path = Path(args[0]) if args else Path(__file__).resolve().parent.parent / "data" / "sample_documents.json"

    Base.metadata.create_all(bind=engine)

    if reset:
        with engine.begin() as conn:
            conn.exec_driver_sql("TRUNCATE TABLE documents RESTART IDENTITY")
        print("Truncated documents table.")

    documents = json.loads(data_path.read_text())
    db = SessionLocal()
    created, duplicates = 0, 0
    start = time.perf_counter()
    try:
        for doc in documents:
            result = repository.create_document(db, title=doc["title"], body=doc["body"])
            if result.created:
                created += 1
            else:
                duplicates += 1
    finally:
        db.close()
    elapsed = time.perf_counter() - start

    print(f"Seeded {created} new documents ({duplicates} duplicates skipped) in {elapsed:.2f}s "
          f"from {data_path}")


if __name__ == "__main__":
    main()
