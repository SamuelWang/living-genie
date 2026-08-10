import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from sse_starlette import EventSourceResponse

from app.chat import (
    build_system_prompt,
    build_user_prompt,
    pending_action_is_confirmed,
    pending_action_reply,
    run_chat_with_tools,
)
from app.db import SessionLocal, get_db
from app.embeddings import embed_texts
from app.models import Conversation, DiaryEntry, Message, MessageReference, Todo, User
from app.schemas import (
    ConversationDetailRead,
    ConversationRead,
    MessageRead,
    MessageReferenceRead,
    SendMessageRequest,
)
from app.security import get_current_user
from app.settings import get_settings
from app.todo_tools import execute_tool
from app.vector_store import search as vector_search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])

_PREVIEW_MAX_LENGTH = 120


def _get_conversation_or_404(
    db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user_id
        )
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return conversation


def _resolve_references(
    db: Session, user_id: uuid.UUID, refs: list[tuple[str, uuid.UUID]]
) -> list[MessageReferenceRead]:
    if not refs:
        return []

    diary_ids = {ref_id for ref_type, ref_id in refs if ref_type == "diary_entry"}
    todo_ids = {ref_id for ref_type, ref_id in refs if ref_type == "todo"}

    diary_entries = (
        {
            entry.id: entry
            for entry in db.scalars(
                select(DiaryEntry).where(
                    DiaryEntry.id.in_(diary_ids), DiaryEntry.user_id == user_id
                )
            )
        }
        if diary_ids
        else {}
    )
    todos = (
        {
            todo.id: todo
            for todo in db.scalars(
                select(Todo).where(Todo.id.in_(todo_ids), Todo.user_id == user_id)
            )
        }
        if todo_ids
        else {}
    )

    resolved: list[MessageReferenceRead] = []
    for ref_type, ref_id in refs:
        if ref_type == "diary_entry":
            entry = diary_entries.get(ref_id)
            resolved.append(
                MessageReferenceRead(
                    source_type="diary_entry",
                    id=ref_id,
                    title=entry.title if entry else None,
                    entry_date=entry.entry_date if entry else None,
                    completed=None,
                )
            )
        else:
            todo = todos.get(ref_id)
            resolved.append(
                MessageReferenceRead(
                    source_type="todo",
                    id=ref_id,
                    title=todo.title if todo else None,
                    entry_date=None,
                    completed=todo.completed if todo else None,
                )
            )
    return resolved


def _preview_for_conversation(db: Session, conversation_id: uuid.UUID) -> str | None:
    first_message = db.scalar(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.role == "user")
        .order_by(Message.created_at)
        .limit(1)
    )
    if first_message is None:
        return None
    content = first_message.content
    if len(content) > _PREVIEW_MAX_LENGTH:
        return content[:_PREVIEW_MAX_LENGTH].rstrip() + "…"
    return content


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ConversationRead:
    conversation = Conversation(user_id=current_user.id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return ConversationRead(
        id=conversation.id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        preview=None,
    )


@router.get("", response_model=list[ConversationRead])
def list_conversations(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[ConversationRead]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = db.scalars(stmt).all()
    return [
        ConversationRead(
            id=conversation.id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            preview=_preview_for_conversation(db, conversation.id),
        )
        for conversation in conversations
    ]


@router.get("/{conversation_id}", response_model=ConversationDetailRead)
def get_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationDetailRead:
    conversation = _get_conversation_or_404(db, conversation_id, current_user.id)
    messages = [
        MessageRead(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            references=_resolve_references(
                db,
                current_user.id,
                [(ref.source_type, ref.source_id) for ref in message.references],
            ),
        )
        for message in conversation.messages
    ]
    return ConversationDetailRead(
        id=conversation.id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        preview=_preview_for_conversation(db, conversation.id),
        messages=messages,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    conversation = _get_conversation_or_404(db, conversation_id, current_user.id)
    db.delete(conversation)
    db.commit()


@router.post("/{conversation_id}/messages")
def send_message(
    conversation_id: uuid.UUID,
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventSourceResponse:
    conversation = _get_conversation_or_404(db, conversation_id, current_user.id)

    user_message = Message(conversation_id=conversation.id, role="user", content=payload.content)
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    settings = get_settings()
    all_refs: list[tuple[str, uuid.UUID]] = []
    seen_refs: set[tuple[str, uuid.UUID]] = set()

    try:
        pending_action = conversation.pending_action
        if pending_action is not None and pending_action_is_confirmed(
            pending_action, payload.content
        ):
            # The genie already proposed this exact action in a prior turn; execute it
            # directly instead of asking the model to re-decide and re-call the tool on a
            # bare "yes" — small local models aren't reliable at that, and free-form text
            # can otherwise narrate success without ever invoking the tool.
            conversation.pending_action = None
            db.commit()
            result = execute_tool(
                db,
                current_user.id,
                pending_action["name"],
                {**pending_action["arguments"], "user_confirmed": True},
            )
            mutated_refs, token_iterator = pending_action_reply(result)
        else:
            conversation.pending_action = None
            db.commit()

            query_vector = embed_texts([payload.content], kind="query")[0]
            points = vector_search(current_user.id, query_vector, settings.retrieval_top_k)

            retrieved_chunks: list[dict] = []
            for point in points:
                point_payload = point.payload or {}
                retrieved_chunks.append(
                    {"date": point_payload["date"], "chunk_text": point_payload["chunk_text"]}
                )
                ref = (point_payload["source_type"], uuid.UUID(point_payload["source_id"]))
                if ref not in seen_refs:
                    seen_refs.add(ref)
                    all_refs.append(ref)

            recent_turns = list(
                reversed(
                    db.scalars(
                        select(Message)
                        .where(
                            Message.conversation_id == conversation.id,
                            Message.id != user_message.id,
                        )
                        .order_by(Message.created_at.desc())
                        .limit(settings.chat_context_turns * 2)
                    ).all()
                )
            )

            system_prompt = build_system_prompt()
            user_prompt = build_user_prompt(payload.content, retrieved_chunks, recent_turns)

            def execute_tool_call(name: str, arguments: dict) -> dict:
                return execute_tool(db, current_user.id, name, arguments)

            mutated_refs, new_pending_action, token_iterator = run_chat_with_tools(
                system_prompt, user_prompt, execute_tool_call
            )
            if new_pending_action is not None:
                conversation.pending_action = new_pending_action
                db.commit()
    except Exception:
        logger.exception("Chat generation failed for conversation %s", conversation.id)

        def error_event_generator():
            yield {
                "event": "error",
                "data": json.dumps({"message": "Something went wrong generating a reply."}),
            }

        return EventSourceResponse(error_event_generator())

    for ref in mutated_refs:
        if ref not in seen_refs:
            seen_refs.add(ref)
            all_refs.append(ref)

    references = _resolve_references(db, current_user.id, all_refs)

    def event_generator():
        yield {
            "event": "references",
            "data": json.dumps(
                {"references": [reference.model_dump(mode="json") for reference in references]}
            ),
        }

        accumulated = ""
        try:
            for token in token_iterator:
                accumulated += token
                yield {"event": "token", "data": json.dumps({"text": token})}
        except Exception:
            logger.exception("Chat generation failed for conversation %s", conversation.id)
            yield {
                "event": "error",
                "data": json.dumps({"message": "Something went wrong generating a reply."}),
            }
            return

        session = SessionLocal()
        try:
            assistant_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=accumulated,
            )
            session.add(assistant_message)
            session.flush()
            for ref_type, ref_id in all_refs:
                session.add(
                    MessageReference(
                        message_id=assistant_message.id, source_type=ref_type, source_id=ref_id
                    )
                )
            session.execute(
                update(Conversation)
                .where(Conversation.id == conversation.id)
                .values(updated_at=func.now())
            )
            session.commit()
            session.refresh(assistant_message)
        finally:
            session.close()

        yield {
            "event": "done",
            "data": json.dumps(
                {
                    "id": str(assistant_message.id),
                    "created_at": assistant_message.created_at.isoformat(),
                }
            ),
        }

    return EventSourceResponse(event_generator())
