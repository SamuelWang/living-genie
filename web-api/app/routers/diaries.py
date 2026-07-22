import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DiaryEntry
from app.schemas import DiaryEntryCreate, DiaryEntryRead, DiaryEntrySummary, DiaryEntryUpdate

router = APIRouter(prefix="/diaries", tags=["diaries"])


def _get_entry_or_404(db: Session, entry_id: uuid.UUID) -> DiaryEntry:
    entry = db.get(DiaryEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found")
    return entry


@router.post("", response_model=DiaryEntryRead, status_code=status.HTTP_201_CREATED)
def create_diary_entry(payload: DiaryEntryCreate, db: Session = Depends(get_db)) -> DiaryEntry:
    entry = DiaryEntry(
        title=payload.title,
        content=payload.content,
        entry_date=payload.entry_date or date.today(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("", response_model=list[DiaryEntrySummary])
def list_diary_entries(db: Session = Depends(get_db)) -> list[DiaryEntry]:
    stmt = select(DiaryEntry).order_by(DiaryEntry.entry_date.desc())
    return list(db.scalars(stmt).all())


@router.get("/{entry_id}", response_model=DiaryEntryRead)
def get_diary_entry(entry_id: uuid.UUID, db: Session = Depends(get_db)) -> DiaryEntry:
    return _get_entry_or_404(db, entry_id)


@router.put("/{entry_id}", response_model=DiaryEntryRead)
def update_diary_entry(
    entry_id: uuid.UUID, payload: DiaryEntryUpdate, db: Session = Depends(get_db)
) -> DiaryEntry:
    entry = _get_entry_or_404(db, entry_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_diary_entry(entry_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    entry = _get_entry_or_404(db, entry_id)
    db.delete(entry)
    db.commit()
