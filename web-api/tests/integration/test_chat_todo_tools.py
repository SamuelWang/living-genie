from tests.conftest import AuthedUser, parse_sse_events


def _post_message(authed_user: AuthedUser, conversation_id: str, content: str = "Please help."):
    return authed_user.client.post(
        f"/conversations/{conversation_id}/messages", json={"content": content}
    )


def _references_of_last_assistant_message(authed_user: AuthedUser, conversation_id: str) -> list[dict]:
    body = authed_user.client.get(f"/conversations/{conversation_id}").json()
    assistant_messages = [m for m in body["messages"] if m["role"] == "assistant"]
    return assistant_messages[-1]["references"]


def test_create_todo_executes_without_user_confirmed(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    fake_ollama_client.tool_call_turns = [
        [{"name": "create_todo", "arguments": {"title": "Buy milk"}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]

    resp = _post_message(authed_user_real_commits, conversation_id, "Add a todo to buy milk.")
    assert resp.status_code == 200, resp.text
    events = parse_sse_events(resp.text)
    assert "error" not in [event for event, _ in events]

    todos = authed_user_real_commits.client.get("/todos").json()
    matching = [t for t in todos if t["title"] == "Buy milk"]
    assert len(matching) == 1

    references = _references_of_last_assistant_message(authed_user_real_commits, conversation_id)
    assert {"source_type": "todo", "id": matching[0]["id"]}.items() <= references[0].items()


def test_complete_todo_does_not_mutate_without_confirmation(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    create_resp = authed_user_real_commits.client.post("/todos", json={"title": "Errand"})
    todo_id = create_resp.json()["id"]

    fake_ollama_client.tool_call_turns = [
        [{"name": "complete_todo", "arguments": {"title": "Errand"}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = _post_message(authed_user_real_commits, conversation_id, "Mark my errand as done.")
    assert resp.status_code == 200, resp.text
    assert "error" not in [event for event, _ in parse_sse_events(resp.text)]

    assert authed_user_real_commits.client.get(f"/todos/{todo_id}").json()["completed"] is False


def test_complete_todo_mutates_when_confirmed(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    create_resp = authed_user_real_commits.client.post("/todos", json={"title": "Errand"})
    todo_id = create_resp.json()["id"]

    fake_ollama_client.tool_call_turns = [
        [{"name": "complete_todo", "arguments": {"title": "Errand", "user_confirmed": True}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = _post_message(authed_user_real_commits, conversation_id, "Yes, mark it done.")
    assert resp.status_code == 200, resp.text

    assert authed_user_real_commits.client.get(f"/todos/{todo_id}").json()["completed"] is True
    references = _references_of_last_assistant_message(authed_user_real_commits, conversation_id)
    assert {"source_type": "todo", "id": todo_id}.items() <= references[0].items()


def test_delete_todo_does_not_mutate_without_confirmation(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    create_resp = authed_user_real_commits.client.post("/todos", json={"title": "Errand"})
    todo_id = create_resp.json()["id"]

    fake_ollama_client.tool_call_turns = [
        [{"name": "delete_todo", "arguments": {"title": "Errand"}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = _post_message(authed_user_real_commits, conversation_id, "Delete my errand.")
    assert resp.status_code == 200, resp.text

    assert authed_user_real_commits.client.get(f"/todos/{todo_id}").status_code == 200


def test_delete_todo_mutates_when_confirmed(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    create_resp = authed_user_real_commits.client.post("/todos", json={"title": "Errand"})
    todo_id = create_resp.json()["id"]

    fake_ollama_client.tool_call_turns = [
        [{"name": "delete_todo", "arguments": {"title": "Errand", "user_confirmed": True}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = _post_message(authed_user_real_commits, conversation_id, "Yes, delete it.")
    assert resp.status_code == 200, resp.text

    assert authed_user_real_commits.client.get(f"/todos/{todo_id}").status_code == 404

    # the reference chip still points at the now-deleted todo (matches _resolve_references'
    # deleted-source fallback: source row gone, but the reference row itself persists).
    references = _references_of_last_assistant_message(authed_user_real_commits, conversation_id)
    assert {"source_type": "todo", "id": todo_id}.items() <= references[0].items()


def test_update_todo_does_not_mutate_without_confirmation(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    create_resp = authed_user_real_commits.client.post("/todos", json={"title": "Errand"})
    todo_id = create_resp.json()["id"]

    fake_ollama_client.tool_call_turns = [
        [
            {
                "name": "update_todo",
                "arguments": {"title": "Errand", "new_title": "Big errand"},
            }
        ]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = _post_message(authed_user_real_commits, conversation_id, "Rename my errand.")
    assert resp.status_code == 200, resp.text

    assert authed_user_real_commits.client.get(f"/todos/{todo_id}").json()["title"] == "Errand"


def test_ambiguous_title_returns_conversational_result_without_mutating(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    first = authed_user_real_commits.client.post("/todos", json={"title": "Errand"}).json()
    second = authed_user_real_commits.client.post("/todos", json={"title": "Errand"}).json()

    fake_ollama_client.tool_call_turns = [
        [{"name": "complete_todo", "arguments": {"title": "Errand", "user_confirmed": True}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = _post_message(authed_user_real_commits, conversation_id, "Mark my errand as done.")
    assert resp.status_code == 200, resp.text
    events = parse_sse_events(resp.text)
    assert "error" not in [event for event, _ in events]
    assert any(event == "done" for event, _ in events)

    assert authed_user_real_commits.client.get(f"/todos/{first['id']}").json()["completed"] is False
    assert authed_user_real_commits.client.get(f"/todos/{second['id']}").json()["completed"] is False


def test_not_found_title_returns_conversational_result_without_raising(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    fake_ollama_client.tool_call_turns = [
        [{"name": "complete_todo", "arguments": {"title": "Nonexistent", "user_confirmed": True}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = _post_message(authed_user_real_commits, conversation_id, "Mark nonexistent as done.")
    assert resp.status_code == 200, resp.text
    events = parse_sse_events(resp.text)
    assert "error" not in [event for event, _ in events]
    assert any(event == "done" for event, _ in events)


def test_cross_user_scoping_only_acts_on_own_todo(
    authed_user_real_commits: AuthedUser,
    other_user_real_commits: AuthedUser,
    fake_vector_store,
    fake_ollama_client,
):
    a_todo = authed_user_real_commits.client.post("/todos", json={"title": "Errand"}).json()
    b_todo = other_user_real_commits.client.post("/todos", json={"title": "Errand"}).json()

    fake_ollama_client.tool_call_turns = [
        [{"name": "complete_todo", "arguments": {"title": "Errand", "user_confirmed": True}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = _post_message(authed_user_real_commits, conversation_id, "Mark my errand as done.")
    assert resp.status_code == 200, resp.text

    assert authed_user_real_commits.client.get(f"/todos/{a_todo['id']}").json()["completed"] is True
    assert other_user_real_commits.client.get(f"/todos/{b_todo['id']}").json()["completed"] is False
