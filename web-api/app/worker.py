import logging
import time

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.chunking import chunk_text
from app.db import SessionLocal
from app.embeddings import embed_texts
from app.models import DiaryEntry, EmbeddingJob
from app.settings import get_settings
from app.vector_store import ensure_collection, upsert_chunks

logger = logging.getLogger(__name__)


def reset_stuck_jobs(db: Session) -> int:
    result = db.execute(
        update(EmbeddingJob).where(EmbeddingJob.status == "processing").values(status="pending")
    )
    db.commit()
    return result.rowcount


def process_next_job(db: Session) -> bool:
    stmt = (
        select(EmbeddingJob)
        .where(EmbeddingJob.status == "pending")
        .order_by(EmbeddingJob.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = db.scalars(stmt).first()
    if job is None:
        db.rollback()
        return False

    job.status = "processing"
    db.commit()

    entry = db.get(DiaryEntry, job.diary_entry_id)
    if entry is None:
        logger.info("Diary entry %s gone; skipping job %s", job.diary_entry_id, job.id)
        return True

    settings = get_settings()
    try:
        chunks = chunk_text(
            entry.content, settings.embedding_chunk_size, settings.embedding_chunk_overlap
        )
        vectors = embed_texts(chunks, kind="passage") if chunks else []
        upsert_chunks(entry.id, entry.user_id, entry.entry_date, chunks, vectors)
        job.status = "completed"
        db.commit()
    except Exception as exc:
        db.rollback()
        _fail_job(db, job.id, exc)

    return True


def _fail_job(db: Session, job_id, exc: Exception) -> None:
    job = db.get(EmbeddingJob, job_id)
    if job is None:
        return
    job.attempts += 1
    if job.attempts < get_settings().embedding_job_max_attempts:
        job.status = "pending"
    else:
        job.status = "failed"
        job.error_message = str(exc)
    db.commit()


def startup() -> None:
    db = SessionLocal()
    try:
        reset_count = reset_stuck_jobs(db)
    finally:
        db.close()
    if reset_count:
        logger.info("Reset %d stuck job(s) from processing to pending", reset_count)
    ensure_collection()


def run_forever() -> None:
    poll_interval = get_settings().embedding_job_poll_interval_seconds
    while True:
        db = SessionLocal()
        try:
            processed = process_next_job(db)
        finally:
            db.close()
        if not processed:
            time.sleep(poll_interval)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    startup()
    run_forever()


if __name__ == "__main__":
    main()
