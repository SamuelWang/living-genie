from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.email import send_password_reset_email, send_verification_email
from app.models import User, UserSession
from app.schemas import (
    ForgotPasswordRequest,
    LocaleUpdate,
    ResendVerificationRequest,
    ResetPasswordRequest,
    UserCreate,
    UserLogin,
    UserRead,
    VerifyEmailRequest,
)
from app.security import (
    consume_email_token,
    create_email_token,
    create_session,
    delete_session,
    get_current_user,
    hash_password,
    invalidate_email_tokens,
    verify_password,
)
from app.settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _in_cooldown(last_sent_at: datetime | None, cooldown_seconds: int) -> bool:
    if last_sent_at is None:
        return False
    return datetime.now(timezone.utc) - last_sent_at < timedelta(seconds=cooldown_seconds)


def _set_session_cookie(response: Response, session: UserSession) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session.id,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        expires=session.expires_at,
        path="/",
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> User:
    email = payload.email.lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        locale=payload.locale,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _, code = create_email_token(db, user.id, "email_verification")
    user.last_verification_email_sent_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    background_tasks.add_task(send_verification_email, user, code)
    return user


@router.post("/login", response_model=UserRead)
def login(payload: UserLogin, response: Response, db: Session = Depends(get_db)) -> User:
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )

    session = create_session(db, user.id)
    _set_session_cookie(response, session)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    settings = get_settings()
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id is not None:
        delete_session(db, session_id)
    response.delete_cookie(key=settings.session_cookie_name, path="/")


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
def resend_verification(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> None:
    settings = get_settings()
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))

    if (
        user is not None
        and user.email_verified_at is None
        and not _in_cooldown(
            user.last_verification_email_sent_at, settings.resend_verification_cooldown_seconds
        )
    ):
        invalidate_email_tokens(db, user.id, "email_verification")
        _, code = create_email_token(db, user.id, "email_verification")
        user.last_verification_email_sent_at = datetime.now(timezone.utc)
        db.commit()
        background_tasks.add_task(send_verification_email, user, code)


@router.post("/verify-email", response_model=UserRead)
def verify_email(
    payload: VerifyEmailRequest, response: Response, db: Session = Depends(get_db)
) -> User:
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))

    token = None
    if user is not None:
        token = consume_email_token(db, user.id, "email_verification", payload.code)

    if user is None or token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code"
        )

    user.email_verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    session = create_session(db, user.id)
    _set_session_cookie(response, session)
    return user


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> None:
    settings = get_settings()
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))

    if user is not None and not _in_cooldown(
        user.last_password_reset_email_sent_at, settings.password_reset_request_cooldown_seconds
    ):
        invalidate_email_tokens(db, user.id, "password_reset")
        _, code = create_email_token(db, user.id, "password_reset")
        user.last_password_reset_email_sent_at = datetime.now(timezone.utc)
        db.commit()
        background_tasks.add_task(send_password_reset_email, user, code)


@router.post("/reset-password", response_model=UserRead)
def reset_password(
    payload: ResetPasswordRequest, response: Response, db: Session = Depends(get_db)
) -> User:
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))

    token = None
    if user is not None:
        token = consume_email_token(db, user.id, "password_reset", payload.code)

    if user is None or token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code"
        )

    user.hashed_password = hash_password(payload.new_password)
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    db.commit()
    db.refresh(user)

    session = create_session(db, user.id)
    _set_session_cookie(response, session)
    return user


@router.put("/locale", response_model=UserRead)
def update_locale(
    payload: LocaleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    current_user.locale = payload.locale
    db.commit()
    db.refresh(current_user)
    return current_user
