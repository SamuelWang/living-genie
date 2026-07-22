import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import UserSession
from app.settings import get_settings
from tests.conftest import AuthedUser, register_and_login

COOKIE_NAME = get_settings().session_cookie_name


def test_register_login_then_full_diary_crud_via_session_cookie(client: TestClient):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    authed = register_and_login(client, email)
    assert COOKIE_NAME in client.cookies

    create_resp = client.post("/diaries", json={"title": "My entry"})
    assert create_resp.status_code == 201
    entry_id = create_resp.json()["id"]

    assert client.get("/diaries").status_code == 200
    assert client.get(f"/diaries/{entry_id}").status_code == 200
    assert client.put(f"/diaries/{entry_id}", json={"title": "Updated"}).status_code == 200
    assert client.delete(f"/diaries/{entry_id}").status_code == 204
    assert authed.user_id is not None


def test_register_duplicate_email_409(client: TestClient):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    first = client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})
    assert first.status_code == 201

    second = client.post("/auth/register", json={"email": email, "password": "different-pass"})
    assert second.status_code == 409


def test_login_wrong_password_401(client: TestClient):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})

    resp = client.post("/auth/login", json={"email": email, "password": "wrong-password"})
    assert resp.status_code == 401


def test_login_nonexistent_email_401(client: TestClient):
    resp = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever1"}
    )
    assert resp.status_code == 401


def test_diaries_without_session_cookie_401(client: TestClient):
    assert client.get("/diaries").status_code == 401
    assert client.post("/diaries", json={"title": "x"}).status_code == 401


def test_diaries_with_invalid_session_cookie_401(client: TestClient):
    client.cookies.set(COOKIE_NAME, "not-a-real-session-token")
    assert client.get("/diaries").status_code == 401


def test_diaries_with_expired_session_401(authed_user: AuthedUser, db_session: Session):
    expired_session = UserSession(
        user_id=authed_user.user_id,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db_session.add(expired_session)
    db_session.commit()

    authed_user.client.cookies.set(COOKIE_NAME, expired_session.id)
    resp = authed_user.client.get("/diaries")
    assert resp.status_code == 401


def test_upload_without_session_401(client: TestClient):
    resp = client.post("/uploads/images", files={"file": ("a.png", b"fake-bytes", "image/png")})
    assert resp.status_code == 401


def test_media_without_session_401(client: TestClient):
    resp = client.get(f"/media/{uuid.uuid4()}/whatever.png")
    assert resp.status_code == 401


def test_logout_invalidates_session(authed_user: AuthedUser):
    client = authed_user.client
    stale_cookie_value = client.cookies.get(COOKIE_NAME)
    assert stale_cookie_value is not None

    logout_resp = client.post("/auth/logout")
    assert logout_resp.status_code == 204

    client.cookies.set(COOKIE_NAME, stale_cookie_value)
    resp = client.get("/diaries")
    assert resp.status_code == 401
