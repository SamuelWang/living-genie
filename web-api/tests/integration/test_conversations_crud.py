import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Conversation, Message
from tests.conftest import AuthedUser


def _create_conversation(authed_user: AuthedUser) -> uuid.UUID:
    resp = authed_user.client.post("/conversations")
    assert resp.status_code == 201, resp.text
    return uuid.UUID(resp.json()["id"])


def test_create_conversation_returns_empty_conversation(authed_user: AuthedUser):
    resp = authed_user.client.post("/conversations")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["preview"] is None
    assert "id" in body and "created_at" in body and "updated_at" in body


def test_list_conversations_orders_by_updated_at_desc(
    authed_user: AuthedUser, db_session: Session
):
    older_id = _create_conversation(authed_user)
    newer_id = _create_conversation(authed_user)

    now = datetime.now(timezone.utc)
    db_session.get(Conversation, older_id).updated_at = now - timedelta(minutes=5)
    db_session.get(Conversation, newer_id).updated_at = now
    db_session.commit()

    resp = authed_user.client.get("/conversations")
    assert resp.status_code == 200, resp.text
    ids = [row["id"] for row in resp.json()]
    assert ids == [str(newer_id), str(older_id)]


def test_list_conversations_preview_is_first_user_message(
    authed_user: AuthedUser, db_session: Session
):
    conversation_id = _create_conversation(authed_user)
    db_session.add(
        Message(conversation_id=conversation_id, role="user", content="What did I do last week?")
    )
    db_session.commit()

    resp = authed_user.client.get("/conversations")
    assert resp.status_code == 200, resp.text
    row = next(row for row in resp.json() if row["id"] == str(conversation_id))
    assert row["preview"] == "What did I do last week?"


def test_get_conversation_resolves_citations(authed_user: AuthedUser, db_session: Session):
    entry_resp = authed_user.client.post("/diaries", json={"title": "Trip", "content": "Draft."})
    entry_id = uuid.UUID(entry_resp.json()["id"])
    conversation_id = _create_conversation(authed_user)

    db_session.add(Message(conversation_id=conversation_id, role="user", content="Tell me about it"))
    db_session.add(
        Message(
            conversation_id=conversation_id,
            role="assistant",
            content="You went on a trip.",
            cited_diary_entry_ids=[entry_id],
        )
    )
    db_session.commit()

    resp = authed_user.client.get(f"/conversations/{conversation_id}")
    assert resp.status_code == 200, resp.text
    messages = resp.json()["messages"]
    assistant_message = next(m for m in messages if m["role"] == "assistant")
    assert len(assistant_message["citations"]) == 1
    citation = assistant_message["citations"][0]
    assert citation["diary_entry_id"] == str(entry_id)
    assert citation["title"] == "Trip"


def test_get_conversation_citation_fallback_for_deleted_entry(
    authed_user: AuthedUser, db_session: Session
):
    deleted_entry_id = uuid.uuid4()
    conversation_id = _create_conversation(authed_user)
    db_session.add(
        Message(
            conversation_id=conversation_id,
            role="assistant",
            content="Reply.",
            cited_diary_entry_ids=[deleted_entry_id],
        )
    )
    db_session.commit()

    resp = authed_user.client.get(f"/conversations/{conversation_id}")
    assert resp.status_code == 200, resp.text
    citation = resp.json()["messages"][0]["citations"][0]
    assert citation["diary_entry_id"] == str(deleted_entry_id)
    assert citation["title"] is None
    assert citation["entry_date"] is None


def test_delete_conversation_removes_it(authed_user: AuthedUser):
    conversation_id = _create_conversation(authed_user)

    delete_resp = authed_user.client.delete(f"/conversations/{conversation_id}")
    assert delete_resp.status_code == 204, delete_resp.text

    get_resp = authed_user.client.get(f"/conversations/{conversation_id}")
    assert get_resp.status_code == 404


def test_cross_user_get_returns_404(authed_user: AuthedUser, other_user: AuthedUser):
    conversation_id = _create_conversation(authed_user)

    resp = other_user.client.get(f"/conversations/{conversation_id}")
    assert resp.status_code == 404


def test_cross_user_delete_returns_404(authed_user: AuthedUser, other_user: AuthedUser):
    conversation_id = _create_conversation(authed_user)

    resp = other_user.client.delete(f"/conversations/{conversation_id}")
    assert resp.status_code == 404
