"""Pure Pydantic schema tests — no DB, no TestClient."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas import DiaryEntryCreate, DiaryEntryUpdate, LocaleUpdate, ResetPasswordRequest


def test_create_missing_title_raises_validation_error():
    with pytest.raises(ValidationError):
        DiaryEntryCreate(content="hello")


def test_create_empty_title_raises_validation_error():
    with pytest.raises(ValidationError):
        DiaryEntryCreate(title="", content="hello")


def test_create_entry_date_optional_at_schema_level():
    entry = DiaryEntryCreate(title="Today")
    assert entry.entry_date is None


def test_create_content_defaults_to_empty_string():
    entry = DiaryEntryCreate(title="Today")
    assert entry.content == ""


def test_create_accepts_explicit_entry_date():
    entry = DiaryEntryCreate(title="Today", entry_date=date(2026, 1, 1))
    assert entry.entry_date == date(2026, 1, 1)


def test_update_all_fields_optional():
    update = DiaryEntryUpdate()
    assert update.title is None
    assert update.content is None
    assert update.entry_date is None


def test_update_empty_title_raises_validation_error():
    with pytest.raises(ValidationError):
        DiaryEntryUpdate(title="")


def test_update_partial_fields_leave_others_unset():
    update = DiaryEntryUpdate(title="New title")
    assert update.model_dump(exclude_unset=True) == {"title": "New title"}


def test_reset_password_request_new_password_too_short_raises_validation_error():
    with pytest.raises(ValidationError):
        ResetPasswordRequest(email="a@example.com", code="ABCD1234", new_password="short1")


def test_reset_password_request_new_password_too_long_raises_validation_error():
    with pytest.raises(ValidationError):
        ResetPasswordRequest(
            email="a@example.com", code="ABCD1234", new_password="a" * 73
        )


def test_reset_password_request_accepts_valid_length_password():
    request = ResetPasswordRequest(
        email="a@example.com", code="ABCD1234", new_password="valid-password-1"
    )
    assert request.new_password == "valid-password-1"


def test_locale_update_rejects_unsupported_locale():
    with pytest.raises(ValidationError):
        LocaleUpdate(locale="fr")


def test_locale_update_accepts_supported_locales():
    assert LocaleUpdate(locale="zh-Hant").locale == "zh-Hant"
    assert LocaleUpdate(locale="en").locale == "en"
