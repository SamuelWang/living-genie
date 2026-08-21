# Living Genie API

Backend API for [Living Genie](../README.md), a personal diary app. FastAPI + SQLAlchemy +
PostgreSQL, providing cookie-session authentication, diary entry CRUD, and image uploads for
entry content. See [../docs/architecture.md](../docs/architecture.md) and
[../docs/requirements/v0.1.0.md](../docs/requirements/v0.1.0.md) for the full design and
acceptance criteria this service implements.

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker (to run PostgreSQL locally)

## Running locally

From the repo root, start Postgres:

```sh
docker compose up -d postgres
```

Then, from `web-api/`:

```sh
cp .env.example .env   # adjust values as needed — see Configuration below
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000`; interactive docs at `http://localhost:8000/docs`.

### Running via Docker

From the repo root:

```sh
cp web-api/.env.example web-api/.env   # adjust values as needed
docker compose up --build web-api
```

Migrations run automatically on container start (`alembic upgrade head`, before `uvicorn`).
Uploaded images persist across restarts via the `uploads_data` named volume, mounted at
`/app/uploads`.

The image applies OS security patches (`apt-get upgrade`) at build time, but that layer is cached
like any other — rebuild periodically with `docker compose build --no-cache --pull web-api` to
actually pick up new upstream patches rather than reusing a stale cached layer.

### Development via Docker Compose (hot reload)

`docker-compose.dev.yaml` overrides `web-api` to run `uvicorn --reload` against the source
bind-mounted from the host, so edits take effect immediately without an image rebuild:

```sh
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build web-api
```

Dependencies (`.venv`) are installed at image-build time and cached in a named volume — if you
change `pyproject.toml`/`uv.lock`, re-run the command above with `--build` to pick up the change.

## Configuration

All settings are read from environment variables (see `app/settings.py`), with `.env.example` as
the source of truth for local defaults:

| Variable               | Default                        | Description                                                                      |
| ---------------------- | ------------------------------- | --------------------------------------------------------------------------------- |
| `DATABASE_URL`          | *(required)*                    | SQLAlchemy connection string, e.g. `postgresql+psycopg://user:pass@host:5432/db`  |
| `UPLOADS_DIR`           | `uploads`                       | Directory (relative or absolute) where uploaded images are stored                 |
| `SESSION_COOKIE_NAME`   | `session_id`                    | Name of the auth session cookie                                                   |
| `SESSION_EXPIRE_MINUTES`| `10080` (7 days)                | Session lifetime                                                                  |
| `COOKIE_SECURE`         | `false`                         | Set `true` in production (HTTPS) so the session cookie requires TLS               |
| `FRONTEND_ORIGIN`       | `http://localhost:5173`         | Allowed CORS origin for the frontend (credentials are allowed)                    |
| `SMTP_HOST`             | `localhost`                     | SMTP server host; Mailpit under `docker-compose.dev.yaml` by default              |
| `SMTP_PORT`             | `1025`                          | SMTP server port (Mailpit's default)                                              |
| `SMTP_USER`             | *(empty)*                       | SMTP auth username; login is skipped entirely when empty                          |
| `SMTP_PASSWORD`         | *(empty)*                       | SMTP auth password                                                                |
| `SMTP_FROM_EMAIL`       | *(required)*                    | `From` address for verification/reset emails                                      |
| `SMTP_FROM_NAME`        | *(required)*                    | `From` display name for verification/reset emails                                 |
| `SMTP_USE_TLS`          | `false`                         | Use STARTTLS when connecting to the SMTP server                                   |
| `EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES` | `1440`         | How long an emailed verification code stays valid                                 |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`     | `30`           | How long an emailed password-reset code stays valid                               |
| `RESEND_VERIFICATION_COOLDOWN_SECONDS`    | `60`           | Minimum interval between verification-email (re)sends to the same account         |
| `PASSWORD_RESET_REQUEST_COOLDOWN_SECONDS` | `60`           | Minimum interval between password-reset email sends to the same account           |
| `EMAIL_CODE_LENGTH`     | `8`                              | Length of generated verification/reset codes                                      |
| `EMAIL_CODE_MAX_ATTEMPTS` | `5`                            | Incorrect code attempts allowed before a code is invalidated                      |

## Database & migrations

Schema changes are managed with Alembic:

```sh
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
uv run alembic downgrade -1
```

## Running tests

```sh
docker compose up -d postgres   # from repo root, if not already running
uv run pytest
```

Tests are split into:
- `tests/unit/` — pure Pydantic schema validation, no database involved.
- `tests/integration/` — full request/response tests against a real PostgreSQL database, covering
  diary CRUD, auth (register/login/logout/session expiry), image upload + media serving, and
  cross-user isolation.

Integration tests automatically provision and migrate a separate `living_genie_test` database on
the same Postgres instance as `DATABASE_URL` (so your dev database is never touched), unless
`TEST_DATABASE_URL` is set to point elsewhere.

`updated_at` refresh-on-edit is covered as an integration test rather than a unit test — it's
refreshed by a server-side Postgres `onupdate=func.now()`, so there's no pure-Python code path to
exercise in isolation.

## Scratch environment for manual verification

For throwaway checks that aren't part of the permanent test suites — registering a user to look
at a UI state, a one-off curl request, poking at a new endpoint — run the app against a dedicated
`living_genie_scratch` database instead of your real dev database:

```sh
uv run python scripts/init_scratch_db.py   # once, or whenever you want a clean slate
DATABASE_URL=postgresql+psycopg://living_genie:living_genie@localhost:5432/living_genie_scratch \
  FRONTEND_ORIGIN=http://localhost:5183 \
  uv run uvicorn app.main:app --reload --port 8090
```

Pair it with the frontend's scratch command (see [../web/README.md](../web/README.md)). See
`CLAUDE.md` at the repo root for when this should be used instead of the normal dev server.

## Project layout

```
app/
├── main.py            # FastAPI app instance, middleware, router registration
├── settings.py        # Environment-driven configuration
├── db.py              # SQLAlchemy engine/session setup
├── models.py          # User, DiaryEntry, UserSession
├── schemas.py         # Pydantic request/response models
├── security.py        # Password hashing, session management, auth dependency
└── routers/
    ├── auth.py        # /auth/register, /auth/login, /auth/logout, /auth/me
    ├── diaries.py      # /diaries CRUD
    └── uploads.py      # /uploads/images, /media/{user_id}/{filename}
alembic/                # Migrations
tests/
├── unit/               # Pure validation tests
└── integration/        # Full-stack tests against a real Postgres database
```
