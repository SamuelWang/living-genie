import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DiaryEntryCreate(BaseModel):
    title: str = Field(min_length=1)
    content: str = ""
    entry_date: date | None = None


class DiaryEntryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    content: str | None = None
    entry_date: date | None = None


class DiaryEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content: str
    entry_date: date
    created_at: datetime
    updated_at: datetime


class DiaryEntrySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    entry_date: date


class UploadResponse(BaseModel):
    url: str
