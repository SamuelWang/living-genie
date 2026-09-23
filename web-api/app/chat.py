import json
import uuid
from datetime import date, timedelta
from typing import Callable, Iterator

from app.embeddings import get_ollama_client
from app.models import Message
from app.observability import get_logger
from app.settings import get_settings
from app.todo_tools import TODO_TOOLS

logger = get_logger(__name__)

_NO_CONTEXT_MARKER = "No relevant diary excerpts were found for this message."
_NO_HISTORY_MARKER = "(no earlier messages in this conversation)"
_WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _build_date_reference(today: date) -> str:
    """Renders this week's and next week's weekday -> date mapping as a lookup table.

    Small local models are unreliable at date *arithmetic* ("today is Friday, so next
    Monday is..."), even when told today's date directly. Giving them a table to look up
    instead of a calculation to perform is far more reliable for phrases like "next
    Monday" / "下週一" / "this Friday" / "這週五".
    """
    this_monday = today - timedelta(days=today.weekday())
    lines = []
    for week_offset, label in [(0, "This week"), (7, "Next week")]:
        monday = this_monday + timedelta(days=week_offset)
        days = ", ".join(
            f"{name} {(monday + timedelta(days=i)).isoformat()}"
            for i, name in enumerate(_WEEKDAY_NAMES)
        )
        lines.append(f"{label}: {days}")
    return "\n".join(lines)


def build_system_prompt() -> str:
    today = date.today()
    return (
        "You are the Living Genie personal assistant. You help the user work with their own "
        "data — diary entries and todos — and understand how to use the Living Genie app.\n\n"
        f"Today's date is {today.isoformat()} ({today.strftime('%A')}). When the user mentions a "
        "relative date (e.g. \"tomorrow\", \"next Monday\", \"下週一\", \"明天\", \"這週五\"), "
        "look up the matching date in this table rather than computing it yourself:\n"
        f"{_build_date_reference(today)}\n\n"
        "Rules:\n"
        "- Whether the user is asking for a todo action (create, update, complete, delete) is "
        "completely independent of the retrieved excerpts below — a todo action is a request to "
        "act, not a question to answer, so never decline or say nothing-relevant-was-found just "
        "because no excerpts matched. For create_todo specifically, call it directly whenever the "
        "user's message asks to add a todo — it needs no confirmation. For update_todo, "
        "complete_todo, and delete_todo, do NOT call them yet at this point — see the confirmation "
        "rule below, which still applies in full and takes precedence. When creating or updating a "
        "todo, pass any due date the user gives as due_date (YYYY-MM-DD); since todos have no "
        "separate time-of-day field, fold any stated time of day into the description instead "
        "(e.g. \"看醫生回診（下午兩點）\") rather than dropping it or inventing a field for it.\n"
        "- Never tell the user a todo was created, updated, completed, or deleted unless you "
        "actually called that exact tool earlier in this turn and it returned success — if you "
        "did not call the tool, do not claim you did.\n"
        "- For everything else, answer only using the retrieved excerpts provided below or general "
        "knowledge about how the Living Genie app works (its features, supported languages, etc.).\n"
        "- Give a direct, specific answer to the user's actual question. Never respond by just "
        "repeating a retrieved excerpt verbatim — read it, then state the answer in your own "
        "words (e.g. if asked what time of day something happened, answer with the time of day, "
        "not the whole excerpt).\n"
        "- If the user is asking a question (not requesting a todo action) and the retrieved "
        "excerpts don't contain information relevant to it, say so plainly instead of guessing or "
        "fabricating an answer.\n"
        "- If multiple retrieved excerpts describe the same topic or event, prefer the one with "
        "the latest date shown in its [date] prefix — especially when the user asks about the "
        "most recent, latest, or last occurrence of something (e.g. \"最近\", \"最新\", \"上次\", "
        "\"last\", \"most recent\", \"latest\").\n"
        "- Before calling update_todo, complete_todo, or delete_todo, ask the user to confirm "
        "exactly which todo and what change first; only call the tool with user_confirmed=true "
        "after the user has explicitly agreed in a prior message — never set it true on your own "
        "judgment. create_todo needs no confirmation. If more than one todo could share the same "
        "title, ask the user for the due date to tell them apart, then pass it as due_date "
        "(YYYY-MM-DD) on the tool call.\n"
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
        f"User's message:\n{question}"
    )


def run_chat_with_tools(
    system_prompt: str,
    user_prompt: str,
    execute_tool_call: Callable[[str, dict], dict],
) -> tuple[list[tuple[str, uuid.UUID]], dict | None, Iterator[str]]:
    """Runs the tool-calling loop eagerly (blocking), then returns the todos mutated
    during that loop, a pending action awaiting confirmation (if any), plus a lazy
    iterator for the final streamed reply.

    Split into an eager phase + a lazy iterator rather than a single generator: the
    caller needs the mutated-references list before streaming starts (to emit the SSE
    references event ahead of tokens), so that part of the work must run synchronously
    — a generator's body wouldn't execute until the caller's first next().
    """
    settings = get_settings()
    client = get_ollama_client()
    # Deciding whether to call a tool is a structured yes/no choice, not creative
    # writing — a low, near-deterministic temperature makes that decision far more
    # reliable. The persona-driven final reply keeps the higher, more expressive
    # temperature separately (reply_options below).
    tool_options = {
        "temperature": settings.ollama_tool_temperature,
        "repeat_penalty": settings.ollama_chat_repeat_penalty,
    }
    reply_options = {
        "temperature": settings.ollama_chat_temperature,
        "repeat_penalty": settings.ollama_chat_repeat_penalty,
    }
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    mutated: list[tuple[str, uuid.UUID]] = []
    hard_failures: list[str] = []
    pending_action: dict | None = None

    for _ in range(settings.chat_tool_max_iterations):
        response = client.chat(
            model=settings.ollama_chat_model,
            messages=messages,
            tools=TODO_TOOLS,
            stream=False,
            think=settings.ollama_chat_think,
            options=tool_options,
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
            elif result.get("ok") is False and result.get("reason") == "needs_confirmation":
                pending_action = {
                    "name": name,
                    "arguments": {k: v for k, v in arguments.items() if k != "user_confirmed"},
                }
            elif result.get("ok") is False:
                hard_failures.append(result.get("message", "The requested change failed."))
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
            options=reply_options,
        )
        for chunk in stream:
            if chunk.message.content:
                yield chunk.message.content

    def _deterministic_failure_reply() -> Iterator[str]:
        # Nothing mutated this turn and at least one confirmed action genuinely failed
        # (as opposed to the expected "needs confirmation" soft-block) — bypass the free-form
        # LLM reply so it can't narrate success it didn't achieve.
        yield "\n\n".join(hard_failures)

    if hard_failures and not mutated:
        return mutated, pending_action, _deterministic_failure_reply()
    return mutated, pending_action, _stream_final_reply()


def pending_action_reply(result: dict) -> tuple[list[tuple[str, uuid.UUID]], Iterator[str]]:
    """Wraps an already-executed tool result into the same shape run_chat_with_tools
    returns, so the router can feed it through the same downstream SSE/persistence code
    without going through the LLM at all — the reply is guaranteed to match what actually
    happened rather than risking a free-form narration.
    """
    mutated: list[tuple[str, uuid.UUID]] = []
    todo_id = result.get("todo_id")
    if todo_id:
        mutated.append(("todo", uuid.UUID(todo_id)))

    def _reply() -> Iterator[str]:
        yield result.get("message", "")

    return mutated, _reply()


_CONFIRMATION_SCHEMA = {
    "type": "object",
    "properties": {"confirmed": {"type": "boolean"}},
    "required": ["confirmed"],
}


def pending_action_is_confirmed(pending_action: dict, user_message: str) -> bool:
    """Asks the model whether the user's latest message confirms a previously proposed
    action. A dedicated, low-temperature, structured-output call kept separate from the
    main tool-calling loop — judging confirmation-vs-not is a natural-language reasoning
    task the model handles far better than any fixed keyword list, and unlike a keyword
    list it needs no maintenance as new languages or phrasings show up.
    """
    settings = get_settings()
    client = get_ollama_client()
    action_description = (
        f"{pending_action['name']} with arguments {json.dumps(pending_action['arguments'])}"
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are checking whether a user's message confirms a previously proposed "
                "action. Respond only with the requested JSON."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Proposed action (awaiting the user's confirmation): {action_description}\n\n"
                f"User's latest message: {user_message}\n\n"
                "Does this message confirm that the proposed action should be performed now?"
            ),
        },
    ]
    response = client.chat(
        model=settings.ollama_chat_model,
        messages=messages,
        stream=False,
        think=settings.ollama_chat_think,
        format=_CONFIRMATION_SCHEMA,
        options={"temperature": 0},
    )
    try:
        return bool(json.loads(response.message.content)["confirmed"])
    except (json.JSONDecodeError, KeyError, TypeError):
        logger.warning(
            "Could not parse confirmation classification response (content=%r); defaulting to False",
            response.message.content,
        )
        return False
