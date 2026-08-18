import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field


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
    locale: Literal["zh-Hant", "en"] = "zh-Hant"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    locale: str
    email_verified_at: datetime | None = Field(exclude=True)
    created_at: datetime

    @computed_field
    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str = Field(min_length=8, max_length=72)


class LocaleUpdate(BaseModel):
    locale: Literal["zh-Hant", "en"]


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
