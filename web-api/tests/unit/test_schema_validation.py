"""Pure Pydantic schema tests — no DB, no TestClient."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas import DiaryEntryCreate, DiaryEntryUpdate


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
