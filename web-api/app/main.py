from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import diaries, uploads
from app.settings import get_settings

app = FastAPI(
    title="Living Genie API",
    description="Backend API for Living Genie.",
    version="0.1.0",
)

_uploads_dir = get_settings().uploads_dir
_uploads_dir.mkdir(parents=True, exist_ok=True)

app.include_router(diaries.router)
app.include_router(uploads.router)
app.mount("/media", StaticFiles(directory=_uploads_dir), name="media")
