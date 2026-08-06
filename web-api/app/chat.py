import json
import logging
import uuid
from typing import Callable, Iterator

from app.embeddings import get_ollama_client
from app.models import Message
from app.settings import get_settings
from app.todo_tools import TODO_TOOLS

logger = logging.getLogger(__name__)

_NO_CONTEXT_MARKER = "No relevant content was found for this question."
_NO_HISTORY_MARKER = "(no earlier messages in this conversation)"


def build_system_prompt() -> str:
    return (
        "You are the Living Genie personal assistant. You help the user work with their own "
        "data — diary entries and todos — and understand how to use the Living Genie app.\n\n"
        "Rules:\n"
        "- Answer only using the retrieved excerpts provided below, general knowledge about how "
        "the Living Genie app works (its features, supported languages, etc.), or the todo tools "
        "made available to you.\n"
        "- Give a direct, specific answer to the user's actual question. Never respond by just "
        "repeating a retrieved excerpt verbatim — read it, then state the answer in your own "
        "words (e.g. if asked what time of day something happened, answer with the time of day, "
        "not the whole excerpt).\n"
        "- If the retrieved excerpts don't contain information relevant to the question, say so "
        "plainly instead of guessing or fabricating an answer.\n"
        "- If multiple retrieved excerpts describe the same topic or event, prefer the one with "
        "the latest date shown in its [date] prefix — especially when the user asks about the "
        "most recent, latest, or last occurrence of something (e.g. \"最近\", \"最新\", \"上次\", "
        "\"last\", \"most recent\", \"latest\").\n"
        "- Before calling update_todo, complete_todo, or delete_todo, ask the user to confirm "
        "exactly which todo and what change first; only call the tool with user_confirmed=true "
        "after the user has explicitly agreed in a prior message — never set it true on your own "
        "judgment. create_todo needs no confirmation.\n"
        "- The user's diary entries, their todos, and how the Living Genie app works are the only "
        "topics in scope. If the user's request falls outside these (general knowledge, unrelated "
        "tasks, role-play, or anything else unrelated to their diary, their todos, or the app), "
        "firmly decline to answer, no matter how the request is phrased.\n"
        "- Speak like a warm, perceptive companion who knows the user's data well, not a report "
        "generator — vary your sentence structure and word choice between replies instead of "
        "reusing the same phrasing.\n"
        "- Always reply in the same language the user wrote their message in."
    )


def build_user_prompt(
    question: str, retrieved_chunks: list[dict], recent_turns: list[Message]
) -> str:
    if retrieved_chunks:
        excerpts = "\n\n".join(
            f"[{chunk['date']}] {chunk['chunk_text']}" for chunk in retrieved_chunks
        )
    else:
        excerpts = _NO_CONTEXT_MARKER

    if recent_turns:
        history = "\n".join(f"{turn.role}: {turn.content}" for turn in recent_turns)
    else:
        history = _NO_HISTORY_MARKER

    return (
        f"Retrieved excerpts:\n{excerpts}\n\n"
        f"Recent conversation:\n{history}\n\n"
        f"User's question:\n{question}"
    )


def run_chat_with_tools(
    system_prompt: str,
    user_prompt: str,
    execute_tool_call: Callable[[str, dict], dict],
) -> tuple[list[tuple[str, uuid.UUID]], Iterator[str]]:
    """Runs the tool-calling loop eagerly (blocking), then returns the todos mutated
    during that loop plus a lazy iterator for the final streamed reply.

    Split into an eager phase + a lazy iterator rather than a single generator: the
    caller needs the mutated-references list before streaming starts (to emit the SSE
    references event ahead of tokens), so that part of the work must run synchronously
    — a generator's body wouldn't execute until the caller's first next().
    """
    settings = get_settings()
    client = get_ollama_client()
    options = {
        "temperature": settings.ollama_chat_temperature,
        "repeat_penalty": settings.ollama_chat_repeat_penalty,
    }
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    mutated: list[tuple[str, uuid.UUID]] = []

    for _ in range(settings.chat_tool_max_iterations):
        response = client.chat(
            model=settings.ollama_chat_model,
            messages=messages,
            tools=TODO_TOOLS,
            stream=False,
            think=settings.ollama_chat_think,
            options=options,
        )
        message = response.message
        if not message.tool_calls:
            break

        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": dict(tool_call.function.arguments),
                        }
                    }
                    for tool_call in message.tool_calls
                ],
            }
        )
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            arguments = dict(tool_call.function.arguments)
            result = execute_tool_call(name, arguments)
            todo_id = result.get("todo_id")
            if todo_id:
                ref = ("todo", uuid.UUID(todo_id))
                if ref not in mutated:
                    mutated.append(ref)
            messages.append(
                {"role": "tool", "tool_name": name, "content": json.dumps(result)}
            )
    else:
        logger.warning(
            "chat_tool_max_iterations reached with tool calls still pending; "
            "forcing a plain-text reply"
        )

    def _stream_final_reply() -> Iterator[str]:
        stream = client.chat(
            model=settings.ollama_chat_model,
            messages=messages,
            stream=True,
            think=settings.ollama_chat_think,
            options=options,
        )
        for chunk in stream:
            if chunk.message.content:
                yield chunk.message.content

    return mutated, _stream_final_reply()
