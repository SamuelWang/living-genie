import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EmbeddingJob
from tests.conftest import AuthedUser


def _jobs_for_todo(db_session: Session, todo_id: uuid.UUID) -> list[EmbeddingJob]:
    return list(
        db_session.scalars(
            select(EmbeddingJob).where(
                EmbeddingJob.source_id == todo_id, EmbeddingJob.source_type == "todo"
            )
        ).all()
    )


def test_create_todo_enqueues_pending_job(authed_user: AuthedUser, db_session: Session):
    resp = authed_user.client.post("/todos", json={"title": "Buy milk"})
    assert resp.status_code == 201, resp.text
    todo_id = uuid.UUID(resp.json()["id"])

    jobs = _jobs_for_todo(db_session, todo_id)
    assert len(jobs) == 1
    assert jobs[0].status == "pending"
    assert jobs[0].attempts == 0


def test_update_title_enqueues_new_job(authed_user: AuthedUser, db_session: Session):
    create_resp = authed_user.client.post("/todos", json={"title": "Buy milk"})
    todo_id = uuid.UUID(create_resp.json()["id"])

    update_resp = authed_user.client.put(f"/todos/{todo_id}", json={"title": "Buy oat milk"})
    assert update_resp.status_code == 200, update_resp.text

    assert len(_jobs_for_todo(db_session, todo_id)) == 2


def test_update_description_enqueues_new_job(authed_user: AuthedUser, db_session: Session):
    create_resp = authed_user.client.post("/todos", json={"title": "Buy milk"})
    todo_id = uuid.UUID(create_resp.json()["id"])

    update_resp = authed_user.client.put(f"/todos/{todo_id}", json={"description": "2%"})
    assert update_resp.status_code == 200, update_resp.text

    assert len(_jobs_for_todo(db_session, todo_id)) == 2


def test_update_completed_enqueues_new_job(authed_user: AuthedUser, db_session: Session):
    create_resp = authed_user.client.post("/todos", json={"title": "Buy milk"})
    todo_id = uuid.UUID(create_resp.json()["id"])

    update_resp = authed_user.client.put(f"/todos/{todo_id}", json={"completed": True})
    assert update_resp.status_code == 200, update_resp.text

    assert len(_jobs_for_todo(db_session, todo_id)) == 2


def test_update_due_date_only_enqueues_new_job(authed_user: AuthedUser, db_session: Session):
    # Unlike diary's title-only-edit exemption, todos re-embed on *any* set field, since
    # due_date feeds the retrieval `date` signal even though it's not part of the chunk text.
    create_resp = authed_user.client.post("/todos", json={"title": "Buy milk"})
    todo_id = uuid.UUID(create_resp.json()["id"])

    update_resp = authed_user.client.put(f"/todos/{todo_id}", json={"due_date": "2026-08-10"})
    assert update_resp.status_code == 200, update_resp.text

    assert len(_jobs_for_todo(db_session, todo_id)) == 2


def test_delete_todo_leaves_job_rows_orphaned(
    authed_user: AuthedUser, db_session: Session, fake_vector_store
):
    # Mirrors test_embedding_indexing.py's diary case: EmbeddingJob.source_id has no FK, so
    # deleting the todo does NOT cascade-delete its job rows.
    create_resp = authed_user.client.post("/todos", json={"title": "Buy milk"})
    todo_id = uuid.UUID(create_resp.json()["id"])
    assert len(_jobs_for_todo(db_session, todo_id)) == 1

    delete_resp = authed_user.client.delete(f"/todos/{todo_id}")
    assert delete_resp.status_code == 204, delete_resp.text

    assert len(_jobs_for_todo(db_session, todo_id)) == 1
