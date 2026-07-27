import uuid
from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.models import DiaryEntry
from tests.conftest import AuthedUser


def test_delete_removes_matching_vector_points(
    authed_user: AuthedUser, db_session: Session, fake_vector_store
):
    create_resp = authed_user.client.post("/diaries", json={"title": "Trip", "content": "Draft."})
    entry_id = uuid.UUID(create_resp.json()["id"])

    fake_vector_store.points[(entry_id, 0)] = {
        "user_id": str(authed_user.user_id),
        "diary_entry_id": str(entry_id),
        "chunk_index": 0,
        "chunk_text": "Draft.",
        "entry_date": date.today().isoformat(),
        "vector": [0.1, 0.2, 0.3],
    }

    delete_resp = authed_user.client.delete(f"/diaries/{entry_id}")

    assert delete_resp.status_code == 204, delete_resp.text
    assert all(point["diary_entry_id"] != str(entry_id) for point in fake_vector_store.points.values())


def test_delete_aborts_postgres_delete_when_vector_store_fails(
    authed_user: AuthedUser, db_session: Session, fake_vector_store
):
    create_resp = authed_user.client.post("/diaries", json={"title": "Trip", "content": "Draft."})
    entry_id = uuid.UUID(create_resp.json()["id"])
    fake_vector_store.fail_delete = True

    with pytest.raises(RuntimeError, match="fake delete failure"):
        authed_user.client.delete(f"/diaries/{entry_id}")

    assert db_session.get(DiaryEntry, entry_id) is not None
