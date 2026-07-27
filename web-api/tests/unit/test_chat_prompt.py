"""Pure chat.py prompt-building tests — no DB, no TestClient.

Citation dedup logic lives inline in app/routers/conversations.py::send_message rather than as a
standalone function, so it's covered as an integration assertion in
tests/integration/test_chat_retrieval_scoping.py instead of here.
"""

from app.chat import build_system_prompt, build_user_prompt
from app.models import Message


def test_build_system_prompt_includes_scope_guarding_rules():
    prompt = build_system_prompt()
    assert "Living Genie" in prompt
    assert "firmly decline" in prompt
    assert "same language" in prompt


def test_build_user_prompt_uses_no_context_marker_when_no_chunks():
    prompt = build_user_prompt("What did I write yesterday?", [], [])
    assert "No relevant diary content was found for this question." in prompt
    assert "What did I write yesterday?" in prompt


def test_build_user_prompt_includes_retrieved_chunks():
    chunks = [
        {"entry_date": "2026-07-20", "chunk_text": "Went hiking."},
        {"entry_date": "2026-07-21", "chunk_text": "Read a book."},
    ]
    prompt = build_user_prompt("What did I do?", chunks, [])
    assert "[2026-07-20] Went hiking." in prompt
    assert "[2026-07-21] Read a book." in prompt


def test_build_user_prompt_uses_no_history_marker_when_no_recent_turns():
    prompt = build_user_prompt("Hello", [], [])
    assert "(no earlier messages in this conversation)" in prompt


def test_build_user_prompt_renders_recent_turns_in_order():
    turns = [
        Message(role="user", content="Hi there"),
        Message(role="assistant", content="Hello! How can I help?"),
    ]
    prompt = build_user_prompt("Follow-up question", [], turns)
    history_section = prompt.split("Recent conversation:\n")[1]
    assert "user: Hi there" in history_section
    assert "assistant: Hello! How can I help?" in history_section
    assert history_section.index("user: Hi there") < history_section.index("assistant: Hello!")
