from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    uploads_dir: Path = Path("uploads")
    session_cookie_name: str = "session_id"
    session_expire_minutes: int = 10080
    cookie_secure: bool = False
    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
