import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models import Todo
from tests.conftest import AuthedUser


def test_delete_removes_matching_vector_points(
    authed_user: AuthedUser, db_session: Session, fake_vector_store
):
    create_resp = authed_user.client.post("/todos", json={"title": "Buy milk"})
    todo_id = uuid.UUID(create_resp.json()["id"])

    fake_vector_store.points[("todo", todo_id, 0)] = {
        "user_id": str(authed_user.user_id),
        "source_type": "todo",
        "source_id": str(todo_id),
        "chunk_index": 0,
        "chunk_text": "Buy milk\n\nStatus: pending",
        "date": date.today().isoformat(),
        "vector": [0.1, 0.2, 0.3],
    }

    delete_resp = authed_user.client.delete(f"/todos/{todo_id}")

    assert delete_resp.status_code == 204, delete_resp.text
    assert all(point["source_id"] != str(todo_id) for point in fake_vector_store.points.values())


def test_delete_aborts_postgres_delete_when_vector_store_fails(
    authed_user: AuthedUser, db_session: Session, fake_vector_store
):
    create_resp = authed_user.client.post("/todos", json={"title": "Buy milk"})
    todo_id = uuid.UUID(create_resp.json()["id"])
    fake_vector_store.fail_delete = True

    delete_resp = authed_user.client.delete(f"/todos/{todo_id}")

    assert delete_resp.status_code == 500, delete_resp.text
    assert db_session.get(Todo, todo_id) is not None
