from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, diaries, uploads
from app.settings import get_settings

_settings = get_settings()

app = FastAPI(
    title="Living Genie API",
    description="Backend API for Living Genie.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_settings.uploads_dir.mkdir(parents=True, exist_ok=True)

app.include_router(auth.router)
app.include_router(diaries.router)
app.include_router(uploads.router)
app.include_router(uploads.media_router)
