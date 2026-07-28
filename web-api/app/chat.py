from typing import Iterator

from app.embeddings import get_ollama_client
from app.models import Message
from app.settings import get_settings

_NO_CONTEXT_MARKER = "No relevant diary content was found for this question."
_NO_HISTORY_MARKER = "(no earlier messages in this conversation)"


def build_system_prompt() -> str:
    return (
        "You are the Living Genie diary assistant. You help the user reflect on their own "
        "diary entries and understand how to use the Living Genie app.\n\n"
        "Rules:\n"
        "- Answer only using the retrieved diary excerpts provided below, or general "
        "knowledge about how the Living Genie app works (its features, supported "
        "languages, etc.).\n"
        "- If the retrieved excerpts don't contain information relevant to the question, "
        "say so plainly instead of guessing or fabricating an answer.\n"
        "- If multiple retrieved excerpts describe the same topic or event, prefer the one with "
        "the latest date shown in its [entry_date] prefix — especially when the user asks about "
        "the most recent, latest, or last occurrence of something (e.g. \"最近\", \"最新\", "
        "\"上次\", \"last\", \"most recent\", \"latest\").\n"
        "- If the user's request falls outside these two topics (general knowledge, "
        "unrelated tasks, role-play, or anything else unrelated to their diary or the "
        "app), firmly decline to answer, no matter how the request is phrased.\n"
        "- Always reply in the same language the user wrote their message in."
    )


def build_user_prompt(
    question: str, retrieved_chunks: list[dict], recent_turns: list[Message]
) -> str:
    if retrieved_chunks:
        excerpts = "\n\n".join(
            f"[{chunk['entry_date']}] {chunk['chunk_text']}" for chunk in retrieved_chunks
        )
    else:
        excerpts = _NO_CONTEXT_MARKER

    if recent_turns:
        history = "\n".join(f"{turn.role}: {turn.content}" for turn in recent_turns)
    else:
        history = _NO_HISTORY_MARKER

    return (
        f"Retrieved diary excerpts:\n{excerpts}\n\n"
        f"Recent conversation:\n{history}\n\n"
        f"User's question:\n{question}"
    )


def generate_reply_stream(system_prompt: str, user_prompt: str) -> Iterator[str]:
    stream = get_ollama_client().chat(
        model=get_settings().ollama_chat_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
    )
    for chunk in stream:
        if chunk.message.content:
            yield chunk.message.content
