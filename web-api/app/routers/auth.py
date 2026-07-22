from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, UserRead
from app.security import (
    create_session,
    delete_session,
    get_current_user,
    hash_password,
    verify_password,
)
from app.settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    email = payload.email.lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = User(email=email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
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

    settings = get_settings()
    session = create_session(db, user.id)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session.id,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        expires=session.expires_at,
        path="/",
    )
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
