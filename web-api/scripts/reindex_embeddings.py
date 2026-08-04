"""One-off migration: drop the Qdrant collection and re-embed everything.

Existing vectors in Qdrant's `entry_chunks` collection are tied to whatever produced them —
the embedding model (dimension, semantics) and the collection's storage config (e.g. vector
distance metric, on-disk/memmap settings). Changing either makes existing vectors incompatible
or leaves them on the old config, not just stale — this deletes the collection outright and
enqueues a fresh EmbeddingJob for every diary entry and every todo, so the worker's normal poll
loop re-embeds everything and Qdrant recreates the collection with the current config from
`app.vector_store.ensure_collection()`.

Run this after updating OLLAMA_EMBEDDING_MODEL, app.vector_store.VECTOR_SIZE, or the vector
storage settings in app.vector_store.ensure_collection(), with the worker stopped (so it can't
race the collection deletion/recreation), then start the worker to let it drain the queued jobs:

    docker compose stop worker
    uv run python scripts/reindex_embeddings.py
    docker compose up -d worker
"""

import sys
from pathlib import Path

WEB_API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WEB_API_ROOT))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import DiaryEntry, EmbeddingJob, Todo  # noqa: E402
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
            db.add(EmbeddingJob(source_type="diary_entry", source_id=entry_id))

        todo_ids = db.scalars(select(Todo.id)).all()
        for todo_id in todo_ids:
            db.add(EmbeddingJob(source_type="todo", source_id=todo_id))

        db.commit()
        print(f"Enqueued {len(entry_ids)} diary entry and {len(todo_ids)} todo embedding job(s)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
