import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.worker as worker
from app.db import SessionLocal
from app.models import EmbeddingJob
from tests.conftest import AuthedUser


def _job_for_entry(db_session: Session, entry_id: uuid.UUID) -> EmbeddingJob:
    return db_session.scalar(
        select(EmbeddingJob).where(EmbeddingJob.diary_entry_id == entry_id)
    )


def test_process_next_job_pending_to_completed(
    authed_user: AuthedUser, db_session: Session, fake_vector_store, fake_ollama_client
):
    create_resp = authed_user.client.post(
        "/diaries", json={"title": "Trip", "content": "Went hiking today. It was fun."}
    )
    entry_id = uuid.UUID(create_resp.json()["id"])
    job = _job_for_entry(db_session, entry_id)
    assert job.status == "pending"

    result = worker.process_next_job(db_session)

    assert result is True
    assert job.status == "completed"
    stored = [point for point in fake_vector_store.points.values() if point["diary_entry_id"] == str(entry_id)]
    assert len(stored) >= 1


def test_process_next_job_returns_false_when_no_pending_job(db_session: Session):
    assert worker.process_next_job(db_session) is False


def test_process_next_job_failure_path_eventually_fails(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    # process_next_job's failure branch calls db.rollback(). The default `db_session` fixture
    # wraps each test in a SAVEPOINT that a real rollback() unwinds past (undoing earlier
    # commits too, not just this call's own writes), so this test needs a real, non-nested
    # session — exactly how worker.run_forever() actually invokes it in production (a fresh
    # SessionLocal() per call).
    create_resp = authed_user_real_commits.client.post(
        "/diaries", json={"title": "Trip", "content": "Went hiking today."}
    )
    entry_id = uuid.UUID(create_resp.json()["id"])
    fake_vector_store.fail_upsert = True

    db = SessionLocal()
    try:
        job = _job_for_entry(db, entry_id)

        assert worker.process_next_job(db) is True
        assert job.attempts == 1
        assert job.status == "pending"

        assert worker.process_next_job(db) is True
        assert job.attempts == 2
        assert job.status == "pending"

        assert worker.process_next_job(db) is True
        assert job.attempts == 3
        assert job.status == "failed"
        assert job.error_message == "fake upsert failure"
    finally:
        db.close()


def test_reset_stuck_jobs_resets_processing_to_pending(
    authed_user: AuthedUser, db_session: Session
):
    create_resp = authed_user.client.post(
        "/diaries", json={"title": "Trip", "content": "Draft."}
    )
    entry_id = uuid.UUID(create_resp.json()["id"])
    job = _job_for_entry(db_session, entry_id)
    job.status = "processing"
    db_session.commit()

    reset_count = worker.reset_stuck_jobs(db_session)

    assert reset_count == 1
    assert job.status == "pending"
