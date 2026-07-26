import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    created_at: datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class CitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    diary_entry_id: uuid.UUID
    title: str | None
    entry_date: date | None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    citations: list[CitationRead]


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    preview: str | None


class ConversationDetailRead(ConversationRead):
    messages: list[MessageRead]


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1)
