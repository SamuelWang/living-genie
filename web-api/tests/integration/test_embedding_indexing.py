import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EmbeddingJob
from tests.conftest import AuthedUser


def _jobs_for_entry(db_session: Session, entry_id: uuid.UUID) -> list[EmbeddingJob]:
    return list(
        db_session.scalars(
            select(EmbeddingJob).where(EmbeddingJob.diary_entry_id == entry_id)
        ).all()
    )


def test_create_diary_entry_enqueues_pending_job(authed_user: AuthedUser, db_session: Session):
    resp = authed_user.client.post(
        "/diaries", json={"title": "Trip", "content": "Went hiking today."}
    )
    assert resp.status_code == 201, resp.text
    entry_id = uuid.UUID(resp.json()["id"])

    jobs = _jobs_for_entry(db_session, entry_id)
    assert len(jobs) == 1
    assert jobs[0].status == "pending"
    assert jobs[0].attempts == 0


def test_update_content_enqueues_new_job(authed_user: AuthedUser, db_session: Session):
    create_resp = authed_user.client.post("/diaries", json={"title": "Trip", "content": "Draft."})
    entry_id = uuid.UUID(create_resp.json()["id"])

    update_resp = authed_user.client.put(
        f"/diaries/{entry_id}", json={"content": "Final version."}
    )
    assert update_resp.status_code == 200, update_resp.text

    jobs = _jobs_for_entry(db_session, entry_id)
    assert len(jobs) == 2


def test_update_title_only_does_not_enqueue_job(authed_user: AuthedUser, db_session: Session):
    create_resp = authed_user.client.post("/diaries", json={"title": "Trip", "content": "Draft."})
    entry_id = uuid.UUID(create_resp.json()["id"])

    update_resp = authed_user.client.put(f"/diaries/{entry_id}", json={"title": "Renamed"})
    assert update_resp.status_code == 200, update_resp.text

    jobs = _jobs_for_entry(db_session, entry_id)
    assert len(jobs) == 1


def test_delete_diary_entry_cascades_job_rows(
    authed_user: AuthedUser, db_session: Session, fake_vector_store
):
    create_resp = authed_user.client.post("/diaries", json={"title": "Trip", "content": "Draft."})
    entry_id = uuid.UUID(create_resp.json()["id"])
    assert len(_jobs_for_entry(db_session, entry_id)) == 1

    delete_resp = authed_user.client.delete(f"/diaries/{entry_id}")
    assert delete_resp.status_code == 204, delete_resp.text

    assert _jobs_for_entry(db_session, entry_id) == []
