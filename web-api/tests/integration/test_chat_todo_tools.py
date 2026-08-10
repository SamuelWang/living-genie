from tests.conftest import AuthedUser, parse_sse_events


def _post_message(authed_user: AuthedUser, conversation_id: str, content: str = "Please help."):
    return authed_user.client.post(
        f"/conversations/{conversation_id}/messages", json={"content": content}
    )


def _references_of_last_assistant_message(authed_user: AuthedUser, conversation_id: str) -> list[dict]:
    body = authed_user.client.get(f"/conversations/{conversation_id}").json()
    assistant_messages = [m for m in body["messages"] if m["role"] == "assistant"]
    return assistant_messages[-1]["references"]


def _content_of_last_assistant_message(authed_user: AuthedUser, conversation_id: str) -> str:
    body = authed_user.client.get(f"/conversations/{conversation_id}").json()
    assistant_messages = [m for m in body["messages"] if m["role"] == "assistant"]
    return assistant_messages[-1]["content"]


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


def test_delete_todo_fuzzy_matches_paraphrased_title(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    create_resp = authed_user_real_commits.client.post(
        "/todos", json={"title": "牙醫回診：洗牙"}
    )
    todo_id = create_resp.json()["id"]

    fake_ollama_client.tool_call_turns = [
        [{"name": "delete_todo", "arguments": {"title": "洗牙", "user_confirmed": True}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = _post_message(
        authed_user_real_commits, conversation_id, "Yes, delete the teeth cleaning todo."
    )
    assert resp.status_code == 200, resp.text

    assert authed_user_real_commits.client.get(f"/todos/{todo_id}").status_code == 404


def test_fuzzy_match_stays_cautious_when_titles_are_similarly_close(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    first = authed_user_real_commits.client.post(
        "/todos", json={"title": "Dentist checkup - teeth cleaning"}
    ).json()
    second = authed_user_real_commits.client.post(
        "/todos", json={"title": "Dentist checkup - annual physical"}
    ).json()

    fake_ollama_client.tool_call_turns = [
        [{"name": "complete_todo", "arguments": {"title": "Dentist checkup", "user_confirmed": True}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = _post_message(authed_user_real_commits, conversation_id, "Mark my dentist checkup as done.")
    assert resp.status_code == 200, resp.text
    events = parse_sse_events(resp.text)
    assert "error" not in [event for event, _ in events]
    assert any(event == "done" for event, _ in events)

    assert authed_user_real_commits.client.get(f"/todos/{first['id']}").json()["completed"] is False
    assert authed_user_real_commits.client.get(f"/todos/{second['id']}").json()["completed"] is False


def test_reply_does_not_claim_success_when_delete_fails_after_confirmation(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    fake_ollama_client.tool_call_turns = [
        [{"name": "delete_todo", "arguments": {"title": "Nonexistent", "user_confirmed": True}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = _post_message(authed_user_real_commits, conversation_id, "Yes, delete the nonexistent todo.")
    assert resp.status_code == 200, resp.text

    reply = _content_of_last_assistant_message(authed_user_real_commits, conversation_id)
    assert reply != "".join(fake_ollama_client.chat_tokens)
    assert "No todo found with title" in reply


def test_delete_todo_disambiguates_same_title_by_due_date(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    target = authed_user_real_commits.client.post(
        "/todos", json={"title": "洗牙", "due_date": "2027-01-30"}
    ).json()
    other = authed_user_real_commits.client.post(
        "/todos", json={"title": "洗牙", "due_date": "2027-03-15"}
    ).json()

    fake_ollama_client.tool_call_turns = [
        [
            {
                "name": "delete_todo",
                "arguments": {
                    "title": "洗牙",
                    "due_date": "2027-01-30",
                    "user_confirmed": True,
                },
            }
        ]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = _post_message(
        authed_user_real_commits, conversation_id, "Yes, delete the 2027/1/30 teeth cleaning."
    )
    assert resp.status_code == 200, resp.text

    assert authed_user_real_commits.client.get(f"/todos/{target['id']}").status_code == 404
    assert authed_user_real_commits.client.get(f"/todos/{other['id']}").status_code == 200


def test_delete_todo_same_title_without_due_date_stays_ambiguous(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    first = authed_user_real_commits.client.post(
        "/todos", json={"title": "洗牙", "due_date": "2027-01-30"}
    ).json()
    second = authed_user_real_commits.client.post(
        "/todos", json={"title": "洗牙", "due_date": "2027-03-15"}
    ).json()

    fake_ollama_client.tool_call_turns = [
        [{"name": "delete_todo", "arguments": {"title": "洗牙", "user_confirmed": True}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = _post_message(authed_user_real_commits, conversation_id, "Yes, delete it.")
    assert resp.status_code == 200, resp.text

    assert authed_user_real_commits.client.get(f"/todos/{first['id']}").status_code == 200
    assert authed_user_real_commits.client.get(f"/todos/{second['id']}").status_code == 200


def test_delete_todo_with_due_date_matching_neither_todo_is_not_found(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    first = authed_user_real_commits.client.post(
        "/todos", json={"title": "洗牙", "due_date": "2027-01-30"}
    ).json()
    second = authed_user_real_commits.client.post(
        "/todos", json={"title": "洗牙", "due_date": "2027-03-15"}
    ).json()

    fake_ollama_client.tool_call_turns = [
        [
            {
                "name": "delete_todo",
                "arguments": {
                    "title": "洗牙",
                    "due_date": "2027-06-01",
                    "user_confirmed": True,
                },
            }
        ]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]
    resp = _post_message(authed_user_real_commits, conversation_id, "Yes, delete it.")
    assert resp.status_code == 200, resp.text

    assert authed_user_real_commits.client.get(f"/todos/{first['id']}").status_code == 200
    assert authed_user_real_commits.client.get(f"/todos/{second['id']}").status_code == 200

    reply = _content_of_last_assistant_message(authed_user_real_commits, conversation_id)
    assert "No todo found with title" in reply
    assert "2027-06-01" in reply


def test_pending_action_executes_on_plain_affirmation_without_model_tool_call(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    create_resp = authed_user_real_commits.client.post(
        "/todos", json={"title": "洗牙", "due_date": "2027-01-30"}
    )
    todo_id = create_resp.json()["id"]

    fake_ollama_client.tool_call_turns = [
        [{"name": "delete_todo", "arguments": {"title": "洗牙", "due_date": "2027-01-30"}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]

    resp1 = _post_message(authed_user_real_commits, conversation_id, "刪除2027/1/30洗牙的待辦")
    assert resp1.status_code == 200, resp1.text
    assert authed_user_real_commits.client.get(f"/todos/{todo_id}").status_code == 200

    # tool_call_turns is exhausted, so the fake model makes NO tool call at all on this
    # turn -- reproduces the real bug where a small model just narrates success from text.
    resp2 = _post_message(authed_user_real_commits, conversation_id, "對")
    assert resp2.status_code == 200, resp2.text

    assert authed_user_real_commits.client.get(f"/todos/{todo_id}").status_code == 404


def test_pending_action_not_executed_when_confirmation_check_says_no(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    create_resp = authed_user_real_commits.client.post(
        "/todos", json={"title": "洗牙", "due_date": "2027-01-30"}
    )
    todo_id = create_resp.json()["id"]

    fake_ollama_client.tool_call_turns = [
        [{"name": "delete_todo", "arguments": {"title": "洗牙", "due_date": "2027-01-30"}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]

    resp1 = _post_message(authed_user_real_commits, conversation_id, "刪除2027/1/30洗牙的待辦")
    assert resp1.status_code == 200, resp1.text

    fake_ollama_client.confirm_pending_action = False
    resp2 = _post_message(authed_user_real_commits, conversation_id, "先不要")
    assert resp2.status_code == 200, resp2.text

    assert authed_user_real_commits.client.get(f"/todos/{todo_id}").status_code == 200


def test_new_proposal_overwrites_stale_pending_action(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client
):
    first = authed_user_real_commits.client.post(
        "/todos", json={"title": "洗牙", "due_date": "2027-01-30"}
    ).json()
    second = authed_user_real_commits.client.post("/todos", json={"title": "買牛奶"}).json()

    # tool_call_turns entries are consumed one per tool-calling *loop iteration*, not one
    # per HTTP turn (a turn's loop keeps calling the model as long as tool_calls keep
    # coming back) -- so the second entry must only be added once turn 1 is done, or
    # turn 1's own loop would consume both in a single request.
    fake_ollama_client.tool_call_turns = [
        [{"name": "delete_todo", "arguments": {"title": "洗牙", "due_date": "2027-01-30"}}]
    ]
    conversation_id = authed_user_real_commits.client.post("/conversations").json()["id"]

    resp1 = _post_message(authed_user_real_commits, conversation_id, "刪除2027/1/30洗牙的待辦")
    assert resp1.status_code == 200, resp1.text

    # This message isn't a confirmation of turn 1's proposal -- it triggers a fresh
    # proposal for a different todo, which should replace the stale pending_action.
    fake_ollama_client.confirm_pending_action = False
    fake_ollama_client.tool_call_turns.append(
        [{"name": "delete_todo", "arguments": {"title": "買牛奶"}}]
    )
    resp2 = _post_message(authed_user_real_commits, conversation_id, "刪除買牛奶")
    assert resp2.status_code == 200, resp2.text

    # Confirming now should act on the LATEST proposal (buy milk), not the stale one.
    fake_ollama_client.confirm_pending_action = True
    resp3 = _post_message(authed_user_real_commits, conversation_id, "對")
    assert resp3.status_code == 200, resp3.text

    assert authed_user_real_commits.client.get(f"/todos/{first['id']}").status_code == 200
    assert authed_user_real_commits.client.get(f"/todos/{second['id']}").status_code == 404


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
