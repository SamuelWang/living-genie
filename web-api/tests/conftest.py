import json
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from psycopg import sql

_TEST_UPLOADS_DIR = Path(__file__).parent / ".uploads-test"

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://living_genie:living_genie@localhost:5432/living_genie_test",
)
os.environ["UPLOADS_DIR"] = str(_TEST_UPLOADS_DIR)

# Only safe to import app.* below this point: app.db creates the SQLAlchemy engine and
# app.main creates the uploads dir at import time, both from the env vars set above.
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db import SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.settings import get_settings  # noqa: E402

WEB_API_ROOT = Path(__file__).resolve().parent.parent


def _maintenance_dsn_and_target_db() -> tuple[str, str]:
    url = get_settings().database_url.replace("+psycopg", "")
    parts = urlsplit(url)
    target_db = parts.path.lstrip("/")
    return urlunsplit(parts._replace(path="/postgres")), target_db


def _ensure_test_database_exists() -> None:
    admin_dsn, target_db = _maintenance_dsn_and_target_db()
    conn = psycopg.connect(admin_dsn, autocommit=True)
    try:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (target_db,)
        ).fetchone()
        if not exists:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_db)))
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def _test_database():
    _ensure_test_database_exists()

    # Base.metadata.drop_all only knows about our own tables, not alembic's own
    # alembic_version tracking table — dropping the schema wholesale guarantees a
    # clean slate (and a real `alembic upgrade head` run) on every session.
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    alembic_cfg = Config(str(WEB_API_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(WEB_API_ROOT / "alembic"))
    command.upgrade(alembic_cfg, "head")

    yield
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _uploads_dir():
    _TEST_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(_TEST_UPLOADS_DIR, ignore_errors=True)


@pytest.fixture
def db_session():
    connection = engine.connect()
    trans = connection.begin()
    TestingSessionLocal = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        if transaction.nested and not transaction._parent.nested:
            sess.begin_nested()

    yield session

    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def second_client(client):
    with TestClient(app) as c:
        yield c


@dataclass
class AuthedUser:
    client: TestClient
    user_id: uuid.UUID
    email: str
    password: str


def register_and_login(
    client: TestClient, email: str, password: str = "correct-horse-1"
) -> AuthedUser:
    resp = client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["id"]

    login_resp = client.post("/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200, login_resp.text

    return AuthedUser(client=client, user_id=uuid.UUID(user_id), email=email, password=password)


@pytest.fixture
def authed_user(client: TestClient) -> AuthedUser:
    return register_and_login(client, f"user-{uuid.uuid4().hex[:8]}@example.com")


@pytest.fixture
def other_user(second_client: TestClient) -> AuthedUser:
    return register_and_login(second_client, f"user-{uuid.uuid4().hex[:8]}@example.com")


@pytest.fixture
def real_commit_client():
    """A client whose requests commit for real, each in its own transaction.

    Unlike `client`, this isn't wrapped in one shared outer transaction/SAVEPOINT, so
    Postgres's `now()` (which is fixed for the lifetime of a transaction) actually
    advances between requests. Needed for tests that must observe a real wall-clock
    gap between two writes (e.g. `updated_at` refresh on edit).
    """

    def _override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

    with SessionLocal() as cleanup_session:
        cleanup_session.query(User).delete()
        cleanup_session.commit()


@pytest.fixture
def authed_user_real_commits(real_commit_client: TestClient) -> AuthedUser:
    return register_and_login(real_commit_client, f"user-{uuid.uuid4().hex[:8]}@example.com")


@pytest.fixture
def second_real_commit_client(real_commit_client: TestClient):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def other_user_real_commits(second_real_commit_client: TestClient) -> AuthedUser:
    return register_and_login(second_real_commit_client, f"user-{uuid.uuid4().hex[:8]}@example.com")


@dataclass
class FakePoint:
    """Mimics qdrant_client.models.ScoredPoint's `.payload` attribute access."""

    payload: dict


class FakeVectorStore:
    """In-memory stand-in for app/vector_store.py, keyed like the real Qdrant collection."""

    def __init__(self):
        self.points: dict[tuple[uuid.UUID, int], dict] = {}
        self.fail_upsert = False
        self.fail_delete = False

    def ensure_collection(self) -> None:
        pass

    def upsert_chunks(
        self,
        diary_entry_id: uuid.UUID,
        user_id: uuid.UUID,
        entry_date: date,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> None:
        if self.fail_upsert:
            raise RuntimeError("fake upsert failure")
        self.delete_diary_entry_points(diary_entry_id, user_id)
        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            self.points[(diary_entry_id, index)] = {
                "user_id": str(user_id),
                "diary_entry_id": str(diary_entry_id),
                "chunk_index": index,
                "chunk_text": chunk,
                "entry_date": entry_date.isoformat(),
                "vector": vector,
            }

    def delete_diary_entry_points(self, diary_entry_id: uuid.UUID, user_id: uuid.UUID) -> None:
        if self.fail_delete:
            raise RuntimeError("fake delete failure")
        for key in [key for key in self.points if key[0] == diary_entry_id]:
            del self.points[key]

    def search(
        self, user_id: uuid.UUID, query_vector: list[float], top_k: int
    ) -> list[FakePoint]:
        matches = [point for point in self.points.values() if point["user_id"] == str(user_id)]
        return [FakePoint(payload=point) for point in matches[:top_k]]


@pytest.fixture
def fake_vector_store(monkeypatch):
    store = FakeVectorStore()
    monkeypatch.setattr("app.worker.ensure_collection", store.ensure_collection)
    monkeypatch.setattr("app.worker.upsert_chunks", store.upsert_chunks)
    monkeypatch.setattr("app.routers.diaries.delete_diary_entry_points", store.delete_diary_entry_points)
    monkeypatch.setattr("app.routers.conversations.vector_search", store.search)
    return store


@dataclass
class FakeOllamaClient:
    """Deterministic stand-in for the ollama.Client used by embeddings.py/chat.py."""

    chat_tokens: list[str] = field(default_factory=lambda: ["This ", "is ", "a ", "canned ", "reply."])
    raise_on_chat: bool = False

    def embed(self, model: str, input: list[str]) -> SimpleNamespace:
        return SimpleNamespace(embeddings=[[0.1, 0.2, 0.3] for _ in input])

    def chat(self, model: str, messages: list[dict], stream: bool = True):
        if self.raise_on_chat:
            raise RuntimeError("fake chat failure")
        for token in self.chat_tokens:
            yield SimpleNamespace(message=SimpleNamespace(content=token))


@pytest.fixture
def fake_ollama_client(monkeypatch):
    client = FakeOllamaClient()
    monkeypatch.setattr("app.embeddings.get_ollama_client", lambda: client)
    monkeypatch.setattr("app.chat.get_ollama_client", lambda: client)
    return client


def parse_sse_events(text: str) -> list[tuple[str, dict]]:
    """Parses an SSE response body into an ordered list of (event, data) pairs."""
    events: list[tuple[str, dict]] = []
    normalized = text.replace("\r\n", "\n")
    for block in normalized.strip("\n").split("\n\n"):
        if not block.strip():
            continue
        event_name = None
        data_lines = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:") :].strip())
        if event_name is not None:
            events.append((event_name, json.loads("".join(data_lines))))
    return events
