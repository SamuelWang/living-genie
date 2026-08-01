import uuid
from datetime import date, datetime
from typing import Literal

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


class TodoCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    due_date: date | None = None


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    due_date: date | None = None
    completed: bool | None = None


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    due_date: date | None
    completed: bool
    created_at: datetime
    updated_at: datetime


class TodoSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    due_date: date | None
    completed: bool


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


class MessageReferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_type: Literal["diary_entry", "todo"]
    id: uuid.UUID
    title: str | None
    entry_date: date | None
    completed: bool | None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    references: list[MessageReferenceRead]


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
