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
    retrieval_candidate_pool_size: int = 20
    retrieval_recency_weight: float = 0.15
    retrieval_recency_half_life_days: int = 180
    chat_context_turns: int = 3
    embedding_job_max_attempts: int = 3
    embedding_job_poll_interval_seconds: float = 2.0
    chat_tool_max_iterations: int = 4
    ollama_chat_temperature: float = 0.9
    ollama_tool_temperature: float = 0.2
    ollama_chat_repeat_penalty: float = 1.3
    ollama_chat_think: bool = True
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str
    smtp_from_name: str
    smtp_use_tls: bool = False
    email_verification_token_expire_minutes: int = 1440
    password_reset_token_expire_minutes: int = 30
    resend_verification_cooldown_seconds: int = 60
    password_reset_request_cooldown_seconds: int = 60
    email_code_length: int = 8
    email_code_max_attempts: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
