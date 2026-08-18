import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EmailToken, User, UserSession
from app.settings import get_settings
from tests.conftest import AuthedUser, FakeEmailSender, register_and_login

COOKIE_NAME = get_settings().session_cookie_name
EMAIL_CODE_MAX_ATTEMPTS = get_settings().email_code_max_attempts


def test_register_login_then_full_diary_crud_via_session_cookie(
    client: TestClient, fake_email_sender: FakeEmailSender
):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    authed = register_and_login(client, email, fake_email_sender)
    assert COOKIE_NAME in client.cookies

    create_resp = client.post("/diaries", json={"title": "My entry"})
    assert create_resp.status_code == 201
    entry_id = create_resp.json()["id"]

    assert client.get("/diaries").status_code == 200
    assert client.get(f"/diaries/{entry_id}").status_code == 200
    assert client.put(f"/diaries/{entry_id}", json={"title": "Updated"}).status_code == 200
    assert client.delete(f"/diaries/{entry_id}").status_code == 204
    assert authed.user_id is not None


def test_register_duplicate_email_409(client: TestClient, fake_email_sender: FakeEmailSender):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    first = client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})
    assert first.status_code == 201

    second = client.post("/auth/register", json={"email": email, "password": "different-pass"})
    assert second.status_code == 409


def test_login_wrong_password_401(client: TestClient, fake_email_sender: FakeEmailSender):
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


def test_register_creates_unverified_account_login_403(
    client: TestClient, fake_email_sender: FakeEmailSender
):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})
    assert resp.status_code == 201
    assert resp.json()["email_verified"] is False

    login_resp = client.post("/auth/login", json={"email": email, "password": "correct-horse-1"})
    assert login_resp.status_code == 403


def test_login_wrong_password_on_unverified_account_401(
    client: TestClient, fake_email_sender: FakeEmailSender
):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})

    resp = client.post("/auth/login", json={"email": email, "password": "wrong-password"})
    assert resp.status_code == 401


def test_verify_email_valid_code_verifies_and_auto_logs_in(
    client: TestClient, fake_email_sender: FakeEmailSender
):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})
    code = fake_email_sender.verification_calls[-1].code

    resp = client.post("/auth/verify-email", json={"email": email, "code": code})
    assert resp.status_code == 200
    assert resp.json()["email_verified"] is True
    assert COOKIE_NAME in client.cookies
    assert client.get("/auth/me").status_code == 200


def test_verify_email_expired_code_400(
    client: TestClient, db_session: Session, fake_email_sender: FakeEmailSender
):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})
    code = fake_email_sender.verification_calls[-1].code

    user = db_session.scalar(select(User).where(User.email == email))
    token = db_session.scalar(
        select(EmailToken).where(
            EmailToken.user_id == user.id, EmailToken.purpose == "email_verification"
        )
    )
    token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    resp = client.post("/auth/verify-email", json={"email": email, "code": code})
    assert resp.status_code == 400


def test_verify_email_already_used_code_400(
    client: TestClient, fake_email_sender: FakeEmailSender
):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})
    code = fake_email_sender.verification_calls[-1].code

    first = client.post("/auth/verify-email", json={"email": email, "code": code})
    assert first.status_code == 200

    second = client.post("/auth/verify-email", json={"email": email, "code": code})
    assert second.status_code == 400


def test_verify_email_lockout_after_max_attempts_400(
    client: TestClient, fake_email_sender: FakeEmailSender
):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})
    correct_code = fake_email_sender.verification_calls[-1].code

    for _ in range(EMAIL_CODE_MAX_ATTEMPTS):
        resp = client.post("/auth/verify-email", json={"email": email, "code": "WRONGCODE"})
        assert resp.status_code == 400

    resp = client.post("/auth/verify-email", json={"email": email, "code": correct_code})
    assert resp.status_code == 400


def test_resend_verification_unregistered_email_202_noop(
    client: TestClient, fake_email_sender: FakeEmailSender
):
    resp = client.post("/auth/resend-verification", json={"email": "nobody@example.com"})
    assert resp.status_code == 202
    assert fake_email_sender.verification_calls == []


def test_resend_verification_already_verified_202_noop(
    authed_user: AuthedUser, fake_email_sender: FakeEmailSender
):
    calls_before = len(fake_email_sender.verification_calls)

    resp = authed_user.client.post(
        "/auth/resend-verification", json={"email": authed_user.email}
    )
    assert resp.status_code == 202
    assert len(fake_email_sender.verification_calls) == calls_before


def test_resend_verification_success_invalidates_prior_code(
    client: TestClient, db_session: Session, fake_email_sender: FakeEmailSender
):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})
    old_code = fake_email_sender.verification_calls[-1].code

    user = db_session.scalar(select(User).where(User.email == email))
    cooldown = get_settings().resend_verification_cooldown_seconds
    user.last_verification_email_sent_at = datetime.now(timezone.utc) - timedelta(
        seconds=cooldown + 1
    )
    db_session.commit()

    resp = client.post("/auth/resend-verification", json={"email": email})
    assert resp.status_code == 202
    assert len(fake_email_sender.verification_calls) == 2
    new_code = fake_email_sender.verification_calls[-1].code
    assert new_code != old_code

    assert (
        client.post("/auth/verify-email", json={"email": email, "code": old_code}).status_code
        == 400
    )
    assert (
        client.post("/auth/verify-email", json={"email": email, "code": new_code}).status_code
        == 200
    )


def test_resend_verification_within_cooldown_202_noop(
    client: TestClient, fake_email_sender: FakeEmailSender
):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})

    resp = client.post("/auth/resend-verification", json={"email": email})
    assert resp.status_code == 202
    assert len(fake_email_sender.verification_calls) == 1


def test_forgot_password_identical_202_for_registered_and_unregistered(
    authed_user: AuthedUser, fake_email_sender: FakeEmailSender
):
    client = authed_user.client

    resp_unregistered = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp_unregistered.status_code == 202
    assert fake_email_sender.reset_calls == []

    resp_registered = client.post("/auth/forgot-password", json={"email": authed_user.email})
    assert resp_registered.status_code == 202
    assert len(fake_email_sender.reset_calls) == 1


def test_reset_password_valid_code_signs_in_and_invalidates_other_sessions(
    authed_user: AuthedUser,
    second_client: TestClient,
    fake_email_sender: FakeEmailSender,
):
    login_resp = second_client.post(
        "/auth/login", json={"email": authed_user.email, "password": authed_user.password}
    )
    assert login_resp.status_code == 200
    other_cookie = second_client.cookies.get(COOKIE_NAME)
    assert other_cookie is not None

    forgot_resp = authed_user.client.post(
        "/auth/forgot-password", json={"email": authed_user.email}
    )
    assert forgot_resp.status_code == 202
    code = fake_email_sender.reset_calls[-1].code

    reset_resp = authed_user.client.post(
        "/auth/reset-password",
        json={"email": authed_user.email, "code": code, "new_password": "new-horse-pass-1"},
    )
    assert reset_resp.status_code == 200
    assert authed_user.client.get("/auth/me").status_code == 200

    second_client.cookies.set(COOKIE_NAME, other_cookie)
    assert second_client.get("/auth/me").status_code == 401

    old_login = authed_user.client.post(
        "/auth/login", json={"email": authed_user.email, "password": authed_user.password}
    )
    assert old_login.status_code == 401
    new_login = authed_user.client.post(
        "/auth/login", json={"email": authed_user.email, "password": "new-horse-pass-1"}
    )
    assert new_login.status_code == 200


def test_reset_password_expired_code_400(
    authed_user: AuthedUser, db_session: Session, fake_email_sender: FakeEmailSender
):
    client = authed_user.client
    client.post("/auth/forgot-password", json={"email": authed_user.email})
    code = fake_email_sender.reset_calls[-1].code

    token = db_session.scalar(
        select(EmailToken).where(
            EmailToken.user_id == authed_user.user_id, EmailToken.purpose == "password_reset"
        )
    )
    token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    resp = client.post(
        "/auth/reset-password",
        json={"email": authed_user.email, "code": code, "new_password": "new-horse-pass-1"},
    )
    assert resp.status_code == 400


def test_reset_password_already_used_code_400(
    authed_user: AuthedUser, fake_email_sender: FakeEmailSender
):
    client = authed_user.client
    client.post("/auth/forgot-password", json={"email": authed_user.email})
    code = fake_email_sender.reset_calls[-1].code

    first = client.post(
        "/auth/reset-password",
        json={"email": authed_user.email, "code": code, "new_password": "new-horse-pass-1"},
    )
    assert first.status_code == 200

    second = client.post(
        "/auth/reset-password",
        json={"email": authed_user.email, "code": code, "new_password": "another-pass-1"},
    )
    assert second.status_code == 400


def test_reset_password_lockout_after_max_attempts_400(
    authed_user: AuthedUser, fake_email_sender: FakeEmailSender
):
    client = authed_user.client
    client.post("/auth/forgot-password", json={"email": authed_user.email})
    correct_code = fake_email_sender.reset_calls[-1].code

    for _ in range(EMAIL_CODE_MAX_ATTEMPTS):
        resp = client.post(
            "/auth/reset-password",
            json={
                "email": authed_user.email,
                "code": "WRONGCODE",
                "new_password": "new-horse-pass-1",
            },
        )
        assert resp.status_code == 400

    resp = client.post(
        "/auth/reset-password",
        json={
            "email": authed_user.email,
            "code": correct_code,
            "new_password": "new-horse-pass-1",
        },
    )
    assert resp.status_code == 400


def test_forgot_password_within_cooldown_202_noop(
    authed_user: AuthedUser, fake_email_sender: FakeEmailSender
):
    client = authed_user.client
    client.post("/auth/forgot-password", json={"email": authed_user.email})
    assert len(fake_email_sender.reset_calls) == 1

    resp = client.post("/auth/forgot-password", json={"email": authed_user.email})
    assert resp.status_code == 202
    assert len(fake_email_sender.reset_calls) == 1


def test_register_persists_locale(client: TestClient, fake_email_sender: FakeEmailSender):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-1", "locale": "en"},
    )
    assert resp.status_code == 201
    assert resp.json()["locale"] == "en"


def test_update_locale_for_signed_in_user(authed_user: AuthedUser):
    resp = authed_user.client.put("/auth/locale", json={"locale": "en"})
    assert resp.status_code == 200
    assert resp.json()["locale"] == "en"


def test_email_sent_uses_current_locale_after_change(
    authed_user: AuthedUser, fake_email_sender: FakeEmailSender
):
    update_resp = authed_user.client.put("/auth/locale", json={"locale": "en"})
    assert update_resp.status_code == 200

    resp = authed_user.client.post("/auth/forgot-password", json={"email": authed_user.email})
    assert resp.status_code == 202
    assert fake_email_sender.reset_calls[-1].locale == "en"
