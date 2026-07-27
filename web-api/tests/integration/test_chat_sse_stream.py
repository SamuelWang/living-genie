import uuid
from datetime import date

from tests.conftest import AuthedUser, parse_sse_events


def _seed_point(fake_vector_store, *, user_id: uuid.UUID, entry_id: uuid.UUID, text: str):
    fake_vector_store.points[(entry_id, 0)] = {
        "user_id": str(user_id),
        "diary_entry_id": str(entry_id),
        "chunk_index": 0,
        "chunk_text": text,
        "entry_date": date.today().isoformat(),
        "vector": [0.1, 0.2, 0.3],
    }


def test_response_content_type_is_event_stream(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = authed_user_real_commits.client.post(
        f"/conversations/{conversation_id}/messages", json={"content": "Hello"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/event-stream")


def test_event_ordering_is_citations_then_tokens_then_done(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = authed_user_real_commits.client.post(
        f"/conversations/{conversation_id}/messages", json={"content": "Hello"}
    )
    events = parse_sse_events(resp.text)
    names = [event for event, _ in events]

    assert names[0] == "citations"
    assert names[-1] == "done"
    assert all(name == "token" for name in names[1:-1])
    assert "token" in names


def test_empty_retrieval_still_returns_200_with_no_citations(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = authed_user_real_commits.client.post(
        f"/conversations/{conversation_id}/messages", json={"content": "Hello"}
    )
    assert resp.status_code == 200, resp.text

    events = parse_sse_events(resp.text)
    citations_event = next(data for event, data in events if event == "citations")
    assert citations_event["citations"] == []
    assert any(event == "done" for event, _ in events)


def test_successful_reply_persists_assistant_message_with_citations(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    entry_resp = authed_user_real_commits.client.post(
        "/diaries", json={"title": "Trip", "content": "Draft."}
    )
    entry_id = uuid.UUID(entry_resp.json()["id"])
    _seed_point(fake_vector_store, user_id=authed_user_real_commits.user_id, entry_id=entry_id, text="Went hiking.")

    create_resp = authed_user_real_commits.client.post("/conversations")
    conversation_id = create_resp.json()["id"]
    created_at = create_resp.json()["updated_at"]

    resp = authed_user_real_commits.client.post(
        f"/conversations/{conversation_id}/messages", json={"content": "Tell me about my trip."}
    )
    assert resp.status_code == 200, resp.text
    events = parse_sse_events(resp.text)
    done_data = next(data for event, data in events if event == "done")

    get_resp = authed_user_real_commits.client.get(f"/conversations/{conversation_id}")
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()

    assistant_message = next(m for m in body["messages"] if m["role"] == "assistant")
    assert assistant_message["id"] == done_data["id"]
    assert assistant_message["content"] == "This is a canned reply."
    assert [c["diary_entry_id"] for c in assistant_message["citations"]] == [str(entry_id)]
    assert body["updated_at"] > created_at


def test_generation_failure_yields_error_event_and_persists_nothing(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    fake_ollama_client.raise_on_chat = True

    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = authed_user_real_commits.client.post(
        f"/conversations/{conversation_id}/messages", json={"content": "Hello"}
    )
    assert resp.status_code == 200, resp.text

    events = parse_sse_events(resp.text)
    names = [event for event, _ in events]
    assert "error" in names
    assert "done" not in names

    get_resp = authed_user_real_commits.client.get(f"/conversations/{conversation_id}")
    assert get_resp.status_code == 200, get_resp.text
    roles = [m["role"] for m in get_resp.json()["messages"]]
    assert roles == ["user"]
