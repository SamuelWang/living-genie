import uuid
from datetime import date

from tests.conftest import AuthedUser, parse_sse_events


def _seed_point(fake_vector_store, *, user_id: uuid.UUID, entry_id: uuid.UUID, chunk_index: int, text: str):
    fake_vector_store.points[(entry_id, chunk_index)] = {
        "user_id": str(user_id),
        "diary_entry_id": str(entry_id),
        "chunk_index": chunk_index,
        "chunk_text": text,
        "entry_date": date.today().isoformat(),
        "vector": [0.1, 0.2, 0.3],
    }


def _citations_from_response(resp) -> list[dict]:
    events = parse_sse_events(resp.text)
    citations_event = next(data for event, data in events if event == "citations")
    return citations_event["citations"]


def test_user_a_never_retrieves_user_b_citations(
    authed_user_real_commits: AuthedUser,
    other_user_real_commits: AuthedUser,
    fake_vector_store,
    fake_ollama_client,
):
    # Both users must go through the real-commit fixtures: the chat endpoint's closing write
    # opens its own SessionLocal(), which can't see rows created inside the SAVEPOINT-wrapped
    # `client`/`db_session` fixture, and `app.dependency_overrides[get_db]` is process-global —
    # only one session strategy can be active for the app at a time.
    a_entry = authed_user_real_commits.client.post(
        "/diaries", json={"title": "A's trip", "content": "Draft."}
    )
    a_entry_id = uuid.UUID(a_entry.json()["id"])
    b_entry = other_user_real_commits.client.post(
        "/diaries", json={"title": "B's trip", "content": "Draft."}
    )
    b_entry_id = uuid.UUID(b_entry.json()["id"])

    shared_text = "Went on an amazing trip to the mountains."
    _seed_point(
        fake_vector_store,
        user_id=authed_user_real_commits.user_id,
        entry_id=a_entry_id,
        chunk_index=0,
        text=shared_text,
    )
    _seed_point(
        fake_vector_store,
        user_id=other_user_real_commits.user_id,
        entry_id=b_entry_id,
        chunk_index=0,
        text=shared_text,
    )

    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = authed_user_real_commits.client.post(
        f"/conversations/{conversation_id}/messages", json={"content": "Tell me about my trip."}
    )
    assert resp.status_code == 200, resp.text

    citations = _citations_from_response(resp)
    cited_ids = {citation["diary_entry_id"] for citation in citations}
    assert cited_ids == {str(a_entry_id)}
    assert str(b_entry_id) not in cited_ids


def test_citations_are_deduped_per_diary_entry(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    entry_resp = authed_user_real_commits.client.post(
        "/diaries", json={"title": "Trip", "content": "Draft."}
    )
    entry_id = uuid.UUID(entry_resp.json()["id"])

    _seed_point(
        fake_vector_store,
        user_id=authed_user_real_commits.user_id,
        entry_id=entry_id,
        chunk_index=0,
        text="Chunk one.",
    )
    _seed_point(
        fake_vector_store,
        user_id=authed_user_real_commits.user_id,
        entry_id=entry_id,
        chunk_index=1,
        text="Chunk two.",
    )

    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = authed_user_real_commits.client.post(
        f"/conversations/{conversation_id}/messages", json={"content": "Tell me about my trip."}
    )
    assert resp.status_code == 200, resp.text

    citations = _citations_from_response(resp)
    matching = [c for c in citations if c["diary_entry_id"] == str(entry_id)]
    assert len(matching) == 1
