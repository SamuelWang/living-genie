"""Pure chat.py::pending_action_is_confirmed tests — no DB, no TestClient."""

from app.chat import pending_action_is_confirmed
from app.settings import get_settings


def test_confirmation_check_passes_think_setting_to_ollama(fake_ollama_client):
    settings = get_settings()
    pending_action = {"name": "delete_todo", "arguments": {"title": "Return library books"}}

    result = pending_action_is_confirmed(pending_action, "Yes, please go ahead.")

    assert result is True
    assert fake_ollama_client.last_confirmation_call_kwargs["think"] == settings.ollama_chat_think
