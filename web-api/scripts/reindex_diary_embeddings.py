"""One-off migration: re-embed every diary entry after an OLLAMA_EMBEDDING_MODEL change.

Existing vectors in Qdrant's `diary_chunks` collection are tied to the embedding model that
produced them (dimension, semantics). Switching models makes them incompatible, not just stale —
this deletes the collection outright and enqueues a fresh EmbeddingJob for every diary entry so
the worker's normal poll loop re-embeds everything with the newly-configured model.

Run this after updating OLLAMA_EMBEDDING_MODEL / app.vector_store.VECTOR_SIZE, with the worker
stopped (so it can't race the collection deletion/recreation), then start the worker to let it
drain the queued jobs:

    docker compose stop worker
    uv run python scripts/reindex_diary_embeddings.py
    docker compose up -d worker
"""

import sys
from pathlib import Path

WEB_API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WEB_API_ROOT))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import DiaryEntry, EmbeddingJob  # noqa: E402
from app.vector_store import COLLECTION_NAME, get_qdrant_client  # noqa: E402


def main() -> None:
    client = get_qdrant_client()
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted Qdrant collection {COLLECTION_NAME!r}")
    else:
        print(f"Qdrant collection {COLLECTION_NAME!r} did not exist; nothing to delete")

    db = SessionLocal()
    try:
        entry_ids = db.scalars(select(DiaryEntry.id)).all()
        for entry_id in entry_ids:
            db.add(EmbeddingJob(diary_entry_id=entry_id))
        db.commit()
        print(f"Enqueued {len(entry_ids)} embedding job(s)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
