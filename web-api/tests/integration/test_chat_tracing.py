from opentelemetry.sdk.trace import ReadableSpan

from tests.conftest import AuthedUser, parse_sse_events


def _send_message(authed_user: AuthedUser, content: str) -> None:
    conversation_id = authed_user.client.post("/conversations").json()["id"]
    resp = authed_user.client.post(
        f"/conversations/{conversation_id}/messages", json={"content": content}
    )
    assert resp.status_code == 200, resp.text
    assert "error" not in [event for event, _ in parse_sse_events(resp.text)]


def _chat_spans(span_exporter) -> dict[str, list[ReadableSpan]]:
    spans: dict[str, list[ReadableSpan]] = {}
    for span in span_exporter.get_finished_spans():
        if span.name.startswith("chat."):
            spans.setdefault(span.name, []).append(span)
    return spans


def test_chat_request_emits_pipeline_spans_with_confirmed_tool_call(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client, span_exporter
):
    authed_user_real_commits.client.post("/todos", json={"title": "Errand"})
    fake_ollama_client.tool_call_turns = [
        [{"name": "complete_todo", "arguments": {"title": "Errand", "user_confirmed": True}}]
    ]

    _send_message(authed_user_real_commits, "Yes, mark my errand done.")

    spans = _chat_spans(span_exporter)
    for name in ("chat.embed_query", "chat.qdrant_search", "chat.build_prompt"):
        assert len(spans[name]) == 1, name

    # one iteration that returns the tool call, then one that returns none and ends the loop
    iterations = sorted(span.attributes["chat.iteration"] for span in spans["chat.ollama_call"])
    assert iterations == [1, 2]

    (tool_span,) = spans["chat.tool_call"]
    assert tool_span.attributes["tool.name"] == "complete_todo"
    assert tool_span.attributes["tool.user_confirmed"] is True
    assert tool_span.attributes["tool.gated"] is False

    trace_ids = {span.context.trace_id for group in spans.values() for span in group}
    assert len(trace_ids) == 1


def test_chat_request_records_gated_tool_call(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client, span_exporter
):
    authed_user_real_commits.client.post("/todos", json={"title": "Errand"})
    fake_ollama_client.tool_call_turns = [
        [{"name": "delete_todo", "arguments": {"title": "Errand"}}]
    ]

    _send_message(authed_user_real_commits, "Delete my errand.")

    (tool_span,) = _chat_spans(span_exporter)["chat.tool_call"]
    assert tool_span.attributes["tool.name"] == "delete_todo"
    assert tool_span.attributes["tool.user_confirmed"] is False
    assert tool_span.attributes["tool.gated"] is True
