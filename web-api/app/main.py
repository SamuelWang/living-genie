import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.db import get_db
from app.routers import auth, conversations, diaries, uploads
from app.settings import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()

app = FastAPI(
    title="Living Genie API",
    description="Backend API for Living Genie.",
    version="0.1.0",
)


class UnhandledExceptionMiddleware(BaseHTTPMiddleware):
    # A handler registered via @app.exception_handler(Exception) is special-cased by Starlette to
    # run in ServerErrorMiddleware, which sits *outside* CORSMiddleware — so its response would
    # still be missing CORS headers, and the browser would still report a CORS failure instead of
    # the real 500. Catching here instead, and registered *before* CORSMiddleware below (so it
    # ends up the innermost of the two, closer to the router), means the JSONResponse we return
    # still passes back out through CORSMiddleware and gets its headers added normally — same as
    # any HTTPException already does.
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> JSONResponse:
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Unhandled exception handling %s %s", request.method, request.url.path)
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.add_middleware(UnhandledExceptionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_settings.uploads_dir.mkdir(parents=True, exist_ok=True)

app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(diaries.router)
app.include_router(uploads.router)
app.include_router(uploads.media_router)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
