import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, UserSession
from app.settings import get_settings

_password_hash = PasswordHash((Argon2Hasher(),))

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
