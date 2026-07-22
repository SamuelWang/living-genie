import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DiaryEntry, User
from app.schemas import DiaryEntryCreate, DiaryEntryRead, DiaryEntrySummary, DiaryEntryUpdate
from app.security import get_current_user

router = APIRouter(prefix="/diaries", tags=["diaries"])


def _get_entry_or_404(db: Session, entry_id: uuid.UUID, user_id: uuid.UUID) -> DiaryEntry:
    entry = db.scalar(
        select(DiaryEntry).where(DiaryEntry.id == entry_id, DiaryEntry.user_id == user_id)
    )
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found")
    return entry


@router.post("", response_model=DiaryEntryRead, status_code=status.HTTP_201_CREATED)
def create_diary_entry(
    payload: DiaryEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiaryEntry:
    entry = DiaryEntry(
        user_id=current_user.id,
        title=payload.title,
        content=payload.content,
        entry_date=payload.entry_date or date.today(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("", response_model=list[DiaryEntrySummary])
def list_diary_entries(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[DiaryEntry]:
    stmt = (
        select(DiaryEntry)
        .where(DiaryEntry.user_id == current_user.id)
        .order_by(DiaryEntry.entry_date.desc())
    )
    return list(db.scalars(stmt).all())


@router.get("/{entry_id}", response_model=DiaryEntryRead)
def get_diary_entry(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiaryEntry:
    return _get_entry_or_404(db, entry_id, current_user.id)


@router.put("/{entry_id}", response_model=DiaryEntryRead)
def update_diary_entry(
    entry_id: uuid.UUID,
    payload: DiaryEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiaryEntry:
    entry = _get_entry_or_404(db, entry_id, current_user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_diary_entry(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    entry = _get_entry_or_404(db, entry_id, current_user.id)
    db.delete(entry)
    db.commit()
