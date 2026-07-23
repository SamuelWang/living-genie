# Architecture

This document describes Living Genie's technical architecture. It is stack-level rather than
phase-specific: it starts with what's needed for [v0.1.0 requirements](requirements/v0.1.0.md)
and is expected to grow (not be rewritten) as later phases — starting with v0.2.0's RAG/Ollama
work — are added. See [roadmap.md](roadmap.md) for the phase breakdown.

## Overview

```
                      REST/JSON                                  SQL
+------------------+                      +------------------+                  +--------------+
|  Frontend (SPA)  | -------------------> |  Backend (API)   | ---------------> |  PostgreSQL  |
|    React + TS    | <------------------- |     FastAPI      | <--------------- |              |
+------------------+                      +------------------+                  +--------------+
  Docker container                          Docker container                    Docker container
```

All three components run as separate Docker containers, orchestrated locally via Docker Compose.

> **Future (v0.2.0+):** an **Ollama** service will be added alongside these containers to serve
> local LLM inference for RAG over diary entries. It is intentionally out of scope for v0.1.0 —
> not present in the v0.1.0 Compose setup — and will be designed when that phase is scoped.

## Frontend

- **Framework**: React + TypeScript
- **Package manager**: pnpm
- **Styling/components**: Tailwind CSS + shadcn/ui
- **Editor**: [Tiptap](https://tiptap.dev/), configured with StarterKit (headings, lists incl.
  task lists, blockquote, code blocks, links) plus GFM tables/strikethrough, a text-style/color
  extension for rich formatting, and an image extension for inline images. Content is serialized
  to/from markdown via `tiptap-markdown`; formatting with no markdown equivalent (e.g. text
  color) is represented as inline HTML within the stored markdown — still valid CommonMark,
  since raw HTML is permitted inline.
- **Data fetching**: REST calls to the FastAPI backend via a typed API client, using
  [TanStack Query](https://tanstack.com/query) for data fetching, caching, and mutations
  (diary CRUD, image uploads) — response shapes match the backend's Pydantic schemas.
- **i18n**: [react-i18next](https://react.i18next.com/) with `i18next-browser-languagedetector`
  for first-visit browser-locale detection. Supported locales: `zh-Hant` (default/fallback) and
  `en`. Translation strings live under `web/src/locales/{lng}/translation.json`, loaded eagerly
  (small string set at this scale). The detected/selected locale is persisted to `localStorage`
  only — no backend involvement, since the preference isn't synced to the account in v0.1.0. A
  language-switcher component (e.g. in the nav) lets the user override the language at any time.
- **Testing**:
  - Vitest + React Testing Library for unit/component tests
  - Playwright for integration/e2e tests of key flows (diary CRUD end-to-end through the UI)
  - No fixed coverage target for v0.1.0

## Backend

- **Framework**: Python + FastAPI
- **Package manager**: [uv](https://docs.astral.sh/uv/)
- **Project layout**: flat `app/` package at the root of `web-api/` (no `src/` indirection),
  following [FastAPI's "Bigger Applications" structure](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
  — `app/main.py`, `app/routers/`, etc. The project is managed as a `uv` application (no
  `[build-system]`/installable-package metadata), since it's run directly via uvicorn rather than
  distributed as a library.
- **Typing**: favor specific, precise types throughout — Pydantic models/enums for
  request/response schemas rather than raw `dict`/`Any`, and typed SQLAlchemy columns for
  persistence models.
- **Database access**: SQLAlchemy ORM, with Alembic for schema migrations.
- **Auth**: server-side session authentication via an `HttpOnly` cookie — `POST /auth/login`
  creates a row in the `sessions` table and sets a `SameSite=Lax` session cookie; the browser then
  sends that cookie automatically on every subsequent request to the API (including `<img>` loads
  of uploaded images, unlike a bearer token, which the browser never attaches to those). All diary,
  upload, and media endpoints require a valid session and operate only on the authenticated user's
  own data. `POST /auth/logout` deletes the session server-side, which a stateless token couldn't
  support. Passwords are hashed with `pwdlib` (Argon2). **Deployment constraint**: because
  `SameSite=Lax` cookies are only sent for same-site requests (same registrable domain, any port),
  the frontend and backend must be deployed under the same site — this replaces the
  origin-agnostic nature the earlier JWT-bearer approach had. CORS is configured with
  `allow_credentials=True` and an explicit `frontend_origin` (not `*`, which the browser rejects
  for credentialed requests) so the cookie is actually sent/accepted across the frontend/backend
  ports.
- **API**: REST endpoints for auth:

  | Method | Path              | Description                          |
  |--------|-------------------|------------------------------------------|
  | POST   | `/auth/register`  | Create a new user account                |
  | POST   | `/auth/login`     | Authenticate; sets the session cookie    |
  | POST   | `/auth/logout`    | Ends the session; clears the cookie      |

  All endpoints below require a valid session cookie and are scoped to the authenticated user.
  Diary CRUD:

  | Method | Path             | Description                        |
  |--------|------------------|-------------------------------------|
  | POST   | `/diaries`       | Create a diary entry                |
  | GET    | `/diaries`       | List diary entries (by entry date)  |
  | GET    | `/diaries/{id}`  | Get a single diary entry            |
  | PUT    | `/diaries/{id}`  | Update a diary entry                |
  | DELETE | `/diaries/{id}`  | Delete a diary entry                |

  Plus one endpoint for image uploads used by the editor:

  | Method | Path              | Description                                          |
  |--------|-------------------|--------------------------------------------------------|
  | POST   | `/uploads/images` | Upload an image, saved to disk; returns its URL for the editor to embed as `![alt](url)` |

- **Media storage**: uploaded images are saved to a directory backed by a dedicated Docker
  volume (separate from the Postgres volume), e.g. mounted at `/app/uploads` in the backend
  container, under a per-user subdirectory (`uploads/{user_id}/...`). Unlike a bare static-file
  mount, `GET /media/{user_id}/{filename}` is a regular authenticated endpoint: it requires a
  valid session and returns 404 (not 403) if the session's user doesn't match `{user_id}`, so both
  upload creation and every subsequent read are access-controlled. The frontend editor embeds the
  returned URL directly into the entry's markdown content. No database table tracks uploads — the
  file on disk plus its reference inside an entry's markdown `content` is the only record,
  consistent with v0.1.0 being kept minimal.

- **Testing**:
  - Unit tests for business logic
  - Integration tests run against a real/test PostgreSQL instance (e.g. pytest)
  - No fixed coverage target for v0.1.0

## Data model

`users` table:

| Column            | Type              | Notes                                   |
|-------------------|-------------------|--------------------------------------------|
| `id`              | uuid, PK          |                                             |
| `email`           | text              | unique, not null                           |
| `hashed_password` | text              | not null, never exposed via API            |
| `created_at`      | timestamptz       | system-set on creation                     |

`diary_entries` table:

| Column       | Type                  | Notes                                   |
|--------------|-----------------------|------------------------------------------|
| `id`         | uuid / serial, PK      |                                          |
| `user_id`    | uuid, FK → `users.id`  | not null, indexed, cascade-deletes with the user |
| `title`      | text                   |                                          |
| `content`    | text                   | markdown                                 |
| `entry_date` | date                   | user-selectable, defaults to today       |
| `created_at` | timestamptz            | system-set on creation                   |
| `updated_at` | timestamptz            | system-set on every update               |

`sessions` table:

| Column       | Type                  | Notes                                    |
|--------------|-----------------------|---------------------------------------------|
| `id`         | text, PK              | opaque random token, stored in the session cookie |
| `user_id`    | uuid, FK → `users.id`  | not null, indexed, cascade-deletes with the user |
| `created_at` | timestamptz            | system-set on creation                      |
| `expires_at` | timestamptz            | session expiry; checked on every request     |

## Containerization

- Separate `Dockerfile` for the frontend and for the backend.
- A root-level `docker-compose.yml` wires together: `web`, `web-api`, and `postgres`
  (with a named volume so diary data persists across restarts), plus a second named volume for
  the backend's uploaded-images directory.
- Configuration via environment variables, e.g. `DATABASE_URL` for the backend's Postgres
  connection. Each service owns its own `.env`/`.env.example` (e.g. `web-api/.env.example`)
  rather than a single shared root file; Compose wires each in per-service via `env_file:`.

## Repository layout (proposed)

```
web/         React + TypeScript app
web-api/     FastAPI app
docs/        Requirements, architecture, roadmap
```

This layout is not created by documentation alone — it will be established when infrastructure
is initialized.

## Future considerations

- **v0.2.0**: adds an Ollama-backed inference service, a vector database for storing embedding
  vectors, and a RAG/chunking pipeline over diary content. This will extend the architecture above
  (new service, new data flows for chunking/embeddings/retrieval) rather than replace it.
