"""Provision and migrate the Postgres database used for ad-hoc manual/agent verification.

Unlike `scripts/init_e2e_db.py`, nothing invokes this automatically — run it by hand (via `uv run
python scripts/init_scratch_db.py`) whenever you want a fresh `living_genie_scratch` to run the
app against for throwaway checks (see the "Scratch environment" section of README.md), instead of
touching the developer's real `living_genie` database.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql

WEB_API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WEB_API_ROOT))

os.environ["DATABASE_URL"] = os.environ.get(
    "SCRATCH_DATABASE_URL",
    "postgresql+psycopg://living_genie:living_genie@localhost:5432/living_genie_scratch",
)

# Only safe to import app.* below this point: app.db creates the SQLAlchemy engine and
# app.main creates the uploads dir at import time, both from the env var set above.
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import engine  # noqa: E402
from app.settings import get_settings  # noqa: E402


def _maintenance_dsn_and_target_db() -> tuple[str, str]:
    url = get_settings().database_url.replace("+psycopg", "")
    parts = urlsplit(url)
    target_db = parts.path.lstrip("/")
    return urlunsplit(parts._replace(path="/postgres")), target_db


def _ensure_database_exists() -> None:
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


def main() -> None:
    _ensure_database_exists()

    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    alembic_cfg = Config(str(WEB_API_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(WEB_API_ROOT / "alembic"))
    command.upgrade(alembic_cfg, "head")
    engine.dispose()


if __name__ == "__main__":
    main()
