import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from sse_starlette import EventSourceResponse

from app.chat import build_system_prompt, build_user_prompt, generate_reply_stream
from app.db import SessionLocal, get_db
from app.embeddings import embed_texts
from app.models import Conversation, DiaryEntry, Message, User
from app.schemas import (
    CitationRead,
    ConversationDetailRead,
    ConversationRead,
    MessageRead,
    SendMessageRequest,
)
from app.security import get_current_user
from app.settings import get_settings
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


def _citations_for_entry_ids(
    db: Session, user_id: uuid.UUID, entry_ids: list[uuid.UUID]
) -> list[CitationRead]:
    if not entry_ids:
        return []
    entries = {
        entry.id: entry
        for entry in db.scalars(
            select(DiaryEntry).where(
                DiaryEntry.id.in_(entry_ids), DiaryEntry.user_id == user_id
            )
        )
    }
    return [
        CitationRead(
            diary_entry_id=entry_id,
            title=entries[entry_id].title if entry_id in entries else None,
            entry_date=entries[entry_id].entry_date if entry_id in entries else None,
        )
        for entry_id in entry_ids
    ]


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
            citations=_citations_for_entry_ids(
                db, current_user.id, message.cited_diary_entry_ids or []
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
    query_vector = embed_texts([payload.content], kind="query")[0]
    points = vector_search(current_user.id, query_vector, settings.retrieval_top_k)

    retrieved_chunks: list[dict] = []
    entry_ids: list[uuid.UUID] = []
    seen_entry_ids: set[uuid.UUID] = set()
    for point in points:
        point_payload = point.payload or {}
        retrieved_chunks.append(
            {
                "entry_date": point_payload["entry_date"],
                "chunk_text": point_payload["chunk_text"],
            }
        )
        entry_id = uuid.UUID(point_payload["diary_entry_id"])
        if entry_id not in seen_entry_ids:
            seen_entry_ids.add(entry_id)
            entry_ids.append(entry_id)

    citations = _citations_for_entry_ids(db, current_user.id, entry_ids)

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

    def event_generator():
        yield {
            "event": "citations",
            "data": json.dumps(
                {"citations": [citation.model_dump(mode="json") for citation in citations]}
            ),
        }

        accumulated = ""
        try:
            for token in generate_reply_stream(system_prompt, user_prompt):
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
                cited_diary_entry_ids=entry_ids or None,
            )
            session.add(assistant_message)
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
