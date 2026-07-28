from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8")

    database_url: str
    uploads_dir: Path = Path("uploads")
    session_cookie_name: str = "session_id"
    session_expire_minutes: int = 10080
    cookie_secure: bool = False
    frontend_origin: str = "http://localhost:5173"
    qdrant_url: str
    ollama_url: str
    ollama_embedding_model: str = "embeddinggemma:300m"
    ollama_chat_model: str = "gemma3:4b"
    embedding_chunk_size: int = 550
    embedding_chunk_overlap: int = 120
    retrieval_top_k: int = 5
    chat_context_turns: int = 3
    embedding_job_max_attempts: int = 3
    embedding_job_poll_interval_seconds: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
