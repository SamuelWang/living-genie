import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
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
