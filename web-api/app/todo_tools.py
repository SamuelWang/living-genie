import logging
import uuid
from datetime import date
from typing import Any, Callable

from sqlalchemy import func, select
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
                "and only then set user_confirmed=true."
            ),
            "parameters": {
                "type": "object",
                "required": ["title", "user_confirmed"],
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Current title identifying the todo.",
                    },
                    "new_title": {"type": "string"},
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
                    "user_confirmed": {"type": "boolean"},
                },
            },
        },
    },
]

_NEEDS_CONFIRMATION: dict = {
    "ok": False,
    "message": (
        "Not performed: ask the user to confirm this exact change first, then call again "
        "with user_confirmed=true."
    ),
}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _find_todo_by_title(db: Session, user_id: uuid.UUID, title: str) -> Todo | dict:
    matches = list(
        db.scalars(
            select(Todo).where(
                Todo.user_id == user_id, func.lower(Todo.title) == title.strip().lower()
            )
        )
    )
    if not matches:
        return {"ok": False, "message": f"No todo found with title '{title}'."}
    if len(matches) > 1:
        return {
            "ok": False,
            "message": (
                f"Multiple todos are titled '{title}'; ask the user which one they mean "
                "(e.g. by due date or description) before proceeding."
            ),
        }
    return matches[0]


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
    new_title: str | None = None,
    new_description: str | None = None,
    new_due_date: str | None = None,
    user_confirmed: bool = False,
) -> dict:
    if user_confirmed is not True:
        return _NEEDS_CONFIRMATION
    found = _find_todo_by_title(db, user_id, title)
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
    db: Session, user_id: uuid.UUID, title: str, user_confirmed: bool = False
) -> dict:
    if user_confirmed is not True:
        return _NEEDS_CONFIRMATION
    found = _find_todo_by_title(db, user_id, title)
    if isinstance(found, dict):
        return found
    todo = found
    todo.completed = True
    db.commit()
    db.refresh(todo)
    _enqueue_reindex(db, todo)
    return {"ok": True, "message": f"Marked '{todo.title}' as completed.", "todo_id": str(todo.id)}


def delete_todo(
    db: Session, user_id: uuid.UUID, title: str, user_confirmed: bool = False
) -> dict:
    if user_confirmed is not True:
        return _NEEDS_CONFIRMATION
    found = _find_todo_by_title(db, user_id, title)
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
