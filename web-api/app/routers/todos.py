import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import EmbeddingJob, Todo, User
from app.schemas import TodoCreate, TodoRead, TodoSummary, TodoUpdate
from app.security import get_current_user
from app.vector_store import delete_source_points

router = APIRouter(prefix="/todos", tags=["todos"])


def _get_todo_or_404(db: Session, todo_id: uuid.UUID, user_id: uuid.UUID) -> Todo:
    todo = db.scalar(select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id))
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    return todo


@router.post("", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
def create_todo(
    payload: TodoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Todo:
    todo = Todo(
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)

    db.add(EmbeddingJob(source_type="todo", source_id=todo.id))
    db.commit()

    return todo


@router.get("", response_model=list[TodoSummary])
def list_todos(
    completed: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Todo]:
    stmt = select(Todo).where(Todo.user_id == current_user.id)
    if completed is not None:
        stmt = stmt.where(Todo.completed == completed)
    stmt = stmt.order_by(
        Todo.completed.asc(), Todo.due_date.asc().nulls_last(), Todo.created_at.desc()
    )
    return list(db.scalars(stmt).all())


@router.get("/{todo_id}", response_model=TodoRead)
def get_todo(
    todo_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Todo:
    return _get_todo_or_404(db, todo_id, current_user.id)


@router.put("/{todo_id}", response_model=TodoRead)
def update_todo(
    todo_id: uuid.UUID,
    payload: TodoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Todo:
    todo = _get_todo_or_404(db, todo_id, current_user.id)
    payload_fields = payload.model_dump(exclude_unset=True)
    for field, value in payload_fields.items():
        setattr(todo, field, value)
    db.commit()
    db.refresh(todo)

    # TodoUpdate only has title/description/due_date/completed, and all four affect either the
    # embedded chunk text or the retrieval date signal, so any non-empty update reembeds.
    if payload_fields:
        db.add(EmbeddingJob(source_type="todo", source_id=todo.id))
        db.commit()

    return todo


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    todo = _get_todo_or_404(db, todo_id, current_user.id)
    delete_source_points("todo", todo.id, current_user.id)
    db.delete(todo)
    db.commit()
