import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import EmailToken, User, UserSession
from app.settings import get_settings

_password_hash = PasswordHash((Argon2Hasher(),))

# Excludes visually ambiguous characters (0/O, 1/I/L) so a hand-typed code isn't misread.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
)


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return _password_hash.verify(password, hashed_password)


def create_session(db: Session, user_id: uuid.UUID) -> UserSession:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.session_expire_minutes)
    session = UserSession(user_id=user_id, expires_at=expires_at)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: Session, session_id: str) -> None:
    session = db.get(UserSession, session_id)
    if session is not None:
        db.delete(session)
        db.commit()


def _email_token_expiry_minutes(purpose: str) -> int:
    settings = get_settings()
    if purpose == "email_verification":
        return settings.email_verification_token_expire_minutes
    if purpose == "password_reset":
        return settings.password_reset_token_expire_minutes
    raise ValueError(f"unknown email token purpose: {purpose}")


def create_email_token(db: Session, user_id: uuid.UUID, purpose: str) -> tuple[EmailToken, str]:
    settings = get_settings()
    code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(settings.email_code_length))
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=_email_token_expiry_minutes(purpose)
    )
    token = EmailToken(user_id=user_id, purpose=purpose, code_hash=code_hash, expires_at=expires_at)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token, code


def invalidate_email_tokens(db: Session, user_id: uuid.UUID, purpose: str) -> None:
    db.execute(
        delete(EmailToken).where(EmailToken.user_id == user_id, EmailToken.purpose == purpose)
    )
    db.commit()


def consume_email_token(
    db: Session, user_id: uuid.UUID, purpose: str, code: str
) -> EmailToken | None:
    settings = get_settings()
    token = (
        db.execute(
            select(EmailToken)
            .where(EmailToken.user_id == user_id, EmailToken.purpose == purpose)
            .order_by(EmailToken.created_at.desc())
        )
        .scalars()
        .first()
    )
    if token is None or token.expires_at < datetime.now(timezone.utc):
        return None

    if hmac.compare_digest(token.code_hash, hashlib.sha256(code.encode()).hexdigest()):
        db.delete(token)
        db.commit()
        return token

    token.attempts += 1
    if token.attempts >= settings.email_code_max_attempts:
        db.delete(token)
    db.commit()
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id is None:
        raise _credentials_exception

    session = db.get(UserSession, session_id)
    if session is None or session.expires_at < datetime.now(timezone.utc):
        raise _credentials_exception

    user = db.get(User, session.user_id)
    if user is None:
        raise _credentials_exception
    return user
