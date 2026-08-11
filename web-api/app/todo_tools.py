import difflib
import logging
import uuid
from datetime import date
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EmbeddingJob, Todo
from app.vector_store import delete_source_points

logger = logging.getLogger(__name__)

TODO_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "create_todo",
            "description": "Create a new todo for the user. Does not require confirmation.",
            "parameters": {
                "type": "object",
                "required": ["title"],
                "properties": {
                    "title": {"type": "string", "description": "Short title of the todo."},
                    "description": {
                        "type": "string",
                        "description": "Optional longer description.",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Optional due date, YYYY-MM-DD.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_todo",
            "description": (
                "Change an existing todo's title, description, or due date. Only call this "
                "after the user has explicitly confirmed the exact change in a prior message, "
                "and only then set user_confirmed=true. Always include `title` (the todo's "
                "CURRENT title, used to find it) even when you are renaming it via `new_title` "
                "— `title` must never be omitted, and it is not the same field as `new_title`."
            ),
            "parameters": {
                "type": "object",
                "required": ["title", "user_confirmed"],
                "properties": {
                    "title": {
                        "type": "string",
                        "description": (
                            "REQUIRED. The todo's CURRENT title, used to find it — always "
                            "include this, even when also renaming via new_title."
                        ),
                    },
                    "due_date": {
                        "type": "string",
                        "description": (
                            "Optional current due date (YYYY-MM-DD) of the todo being changed, "
                            "used to tell it apart from other todos sharing the same title."
                        ),
                    },
                    "new_title": {
                        "type": "string",
                        "description": "The new title to rename it to, if renaming. Not a substitute for `title`.",
                    },
                    "new_description": {"type": "string"},
                    "new_due_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "user_confirmed": {"type": "boolean"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_todo",
            "description": "Mark a todo as completed. Requires prior user confirmation.",
            "parameters": {
                "type": "object",
                "required": ["title", "user_confirmed"],
                "properties": {
                    "title": {"type": "string"},
                    "due_date": {
                        "type": "string",
                        "description": (
                            "Optional due date (YYYY-MM-DD) of the todo, used to tell it apart "
                            "from other todos sharing the same title."
                        ),
                    },
                    "user_confirmed": {"type": "boolean"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_todo",
            "description": "Permanently delete a todo. Requires prior user confirmation.",
            "parameters": {
                "type": "object",
                "required": ["title", "user_confirmed"],
                "properties": {
                    "title": {"type": "string"},
                    "due_date": {
                        "type": "string",
                        "description": (
                            "Optional due date (YYYY-MM-DD) of the todo, used to tell it apart "
                            "from other todos sharing the same title."
                        ),
                    },
                    "user_confirmed": {"type": "boolean"},
                },
            },
        },
    },
]

_NEEDS_CONFIRMATION: dict = {
    "ok": False,
    "reason": "needs_confirmation",
    "message": (
        "Not performed: ask the user to confirm this exact change first, then call again "
        "with user_confirmed=true."
    ),
}

_FUZZY_MATCH_THRESHOLD = 0.6
_FUZZY_MATCH_MARGIN = 0.15


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _title_similarity(search: str, candidate: str) -> float:
    if search == candidate:
        return 1.0
    if search in candidate or candidate in search:
        return 0.9
    return difflib.SequenceMatcher(None, search, candidate).ratio()


def _ambiguous_error(title: str, due_date: date | None) -> dict:
    if due_date is not None:
        hint = "ask the user for more distinguishing detail (e.g. the description) before proceeding"
    else:
        hint = "ask the user for the due date (or other distinguishing detail) before proceeding"
    return {
        "ok": False,
        "message": f"Multiple todos could match '{title}'; {hint}.",
    }


def _not_found_error(title: str, due_date: date | None) -> dict:
    if due_date is not None:
        return {
            "ok": False,
            "message": f"No todo found with title '{title}' due {due_date.isoformat()}.",
        }
    return {"ok": False, "message": f"No todo found with title '{title}'."}


def _find_todo_by_title(
    db: Session, user_id: uuid.UUID, title: str, due_date: str | None = None
) -> Todo | dict:
    search = title.strip().lower()
    parsed_due_date = _parse_date(due_date)
    candidates = list(db.scalars(select(Todo).where(Todo.user_id == user_id)))
    if parsed_due_date is not None:
        candidates = [t for t in candidates if t.due_date == parsed_due_date]
    if not candidates:
        return _not_found_error(title, parsed_due_date)

    exact = [t for t in candidates if t.title.strip().lower() == search]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return _ambiguous_error(title, parsed_due_date)

    scored = sorted(
        candidates,
        key=lambda t: _title_similarity(search, t.title.strip().lower()),
        reverse=True,
    )
    best_score = _title_similarity(search, scored[0].title.strip().lower())
    if best_score < _FUZZY_MATCH_THRESHOLD:
        return _not_found_error(title, parsed_due_date)
    if len(scored) > 1:
        second_score = _title_similarity(search, scored[1].title.strip().lower())
        if second_score >= best_score - _FUZZY_MATCH_MARGIN:
            return _ambiguous_error(title, parsed_due_date)
    return scored[0]


def _enqueue_reindex(db: Session, todo: Todo) -> None:
    db.add(EmbeddingJob(source_type="todo", source_id=todo.id))
    db.commit()


def create_todo(
    db: Session,
    user_id: uuid.UUID,
    title: str,
    description: str | None = None,
    due_date: str | None = None,
) -> dict:
    todo = Todo(
        user_id=user_id,
        title=title,
        description=description,
        due_date=_parse_date(due_date),
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    _enqueue_reindex(db, todo)
    return {"ok": True, "message": f"Created todo '{todo.title}'.", "todo_id": str(todo.id)}


def update_todo(
    db: Session,
    user_id: uuid.UUID,
    title: str,
    due_date: str | None = None,
    new_title: str | None = None,
    new_description: str | None = None,
    new_due_date: str | None = None,
    user_confirmed: bool = False,
) -> dict:
    if user_confirmed is not True:
        return _NEEDS_CONFIRMATION
    found = _find_todo_by_title(db, user_id, title, due_date)
    if isinstance(found, dict):
        return found
    todo = found
    if new_title is not None:
        todo.title = new_title
    if new_description is not None:
        todo.description = new_description
    if new_due_date is not None:
        todo.due_date = _parse_date(new_due_date)
    db.commit()
    db.refresh(todo)
    _enqueue_reindex(db, todo)
    return {"ok": True, "message": f"Updated todo '{todo.title}'.", "todo_id": str(todo.id)}


def complete_todo(
    db: Session,
    user_id: uuid.UUID,
    title: str,
    due_date: str | None = None,
    user_confirmed: bool = False,
) -> dict:
    if user_confirmed is not True:
        return _NEEDS_CONFIRMATION
    found = _find_todo_by_title(db, user_id, title, due_date)
    if isinstance(found, dict):
        return found
    todo = found
    todo.completed = True
    db.commit()
    db.refresh(todo)
    _enqueue_reindex(db, todo)
    return {"ok": True, "message": f"Marked '{todo.title}' as completed.", "todo_id": str(todo.id)}


def delete_todo(
    db: Session,
    user_id: uuid.UUID,
    title: str,
    due_date: str | None = None,
    user_confirmed: bool = False,
) -> dict:
    if user_confirmed is not True:
        return _NEEDS_CONFIRMATION
    found = _find_todo_by_title(db, user_id, title, due_date)
    if isinstance(found, dict):
        return found
    todo = found
    delete_source_points("todo", todo.id, user_id)
    todo_id, todo_title = todo.id, todo.title
    db.delete(todo)
    db.commit()
    return {"ok": True, "message": f"Deleted todo '{todo_title}'.", "todo_id": str(todo_id)}


_HANDLERS: dict[str, Callable[..., dict]] = {
    "create_todo": create_todo,
    "update_todo": update_todo,
    "complete_todo": complete_todo,
    "delete_todo": delete_todo,
}


def execute_tool(db: Session, user_id: uuid.UUID, name: str, arguments: dict[str, Any]) -> dict:
    handler = _HANDLERS.get(name)
    if handler is None:
        return {"ok": False, "message": f"Unknown tool '{name}'."}
    try:
        return handler(db, user_id, **arguments)
    except TypeError:
        logger.warning("Bad arguments for tool %s: %r", name, arguments)
        return {"ok": False, "message": "Invalid arguments for this tool call."}
