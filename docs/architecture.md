# Architecture

This document describes Living Genie's technical architecture. It is stack-level rather than
phase-specific: it currently covers [v0.1.0](requirements/v0.1.0.md) and
[v0.2.0](requirements/v0.2.0.md), and is expected to keep growing (not be rewritten) as later
phases are added. See [roadmap.md](roadmap.md) for the phase breakdown.

## Overview

```
                      REST/JSON                                  SQL
+------------------+                      +------------------+                  +--------------+
|  Frontend (SPA)  | -------------------> |  Backend (API)   | ---------------> |  PostgreSQL  |
|    React + TS    | <------------------- |     FastAPI      | <--------------- |  (+ job table)|
+------------------+                      +------------------+                  +--------------+
  Docker container                         Docker container    |    ^            Docker container
                                    embed query /                |    | poll
                                    generate reply                v    | embedding_jobs
                                    +------------+          +------------------+
                                    |            |<-------- |  Indexing Worker |
                                    v            v          +------------------+
                              +----------+  +----------+       |            |
                              |  Ollama  |  |  Qdrant  |<------+            |
                              | (LLM +   |  | (vector  |   upsert/delete   embed
                              | embed)   |  |  store)  |     vectors      chunks
                              +----------+  +----------+
                              Docker container  Docker container
```

All components run as separate Docker containers, orchestrated locally via Docker Compose. Both
the backend (for synchronous chat queries) and the indexing worker (for background chunking/
embedding) call Ollama and Qdrant directly — neither proxies through the other.

## Frontend

- **Framework**: React + TypeScript
- **Package manager**: pnpm
- **Styling/components**: Tailwind CSS + shadcn/ui
- **Editor**: [Tiptap](https://tiptap.dev/), configured with StarterKit (headings, lists incl.
  task lists, blockquote, code blocks, links) plus GFM tables/strikethrough, a text-style/color
  extension for rich formatting, and an image extension for inline images. Content is serialized
  to/from markdown via `@tiptap/markdown`; formatting with no markdown equivalent (e.g. text
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

  Chat (see [AI / RAG pipeline](#ai--rag-pipeline) below):

  | Method | Path                          | Description                                         |
  |--------|-------------------------------|------------------------------------------------------|
  | POST   | `/conversations`              | Create a new conversation                             |
  | GET    | `/conversations`               | List the user's conversations, most recently active first |
  | GET    | `/conversations/{id}`          | Get a conversation with its messages                  |
  | DELETE | `/conversations/{id}`          | Delete a conversation                                  |
  | POST   | `/conversations/{id}/messages` | Send a message; streams back the RAG-grounded reply    |

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

## AI / RAG pipeline

- **Local inference**: an `ollama` service serves both embedding and chat generation; model tags
  are configurable via `OLLAMA_EMBEDDING_MODEL` (default `multilingual-e5-large`) and
  `OLLAMA_CHAT_MODEL` (default `gemma2:9b`, with `gemma2:2b` as a lighter option for constrained
  hardware) environment variables. Both are non-China-origin, open-weight models sized to run
  CPU-only. `multilingual-e5-large` (Microsoft Research) was chosen over the smaller, more common
  `nomic-embed-text` because it's explicitly multilingual-trained (including Chinese), which
  matters since diary content is expected to be mostly Traditional Chinese; it's pulled from a
  community-published GGUF quantization rather than Ollama's official curated library. `gemma2`
  (Google) was chosen for chat generation for its license permissiveness and reasonable
  multilingual coverage. Models are pulled on first startup via a one-shot init step (a
  short-lived service running `ollama pull` against the `ollama` service, exiting once done).

- **Chunking**: on diary entry create/update, `web-api` enqueues a row in `embedding_jobs` with
  status `pending` rather than embedding inline, keeping the save request fast.

- **Indexing worker**: a dedicated `worker` process (same build as `web-api`, different command)
  polls `embedding_jobs` for pending rows using `SELECT ... FOR UPDATE SKIP LOCKED` (safe under
  concurrent polling), splits the entry's markdown `content` into paragraph-aware chunks with
  overlap, embeds each chunk via Ollama, and upserts the resulting vectors into Qdrant —
  replacing any prior points for that `diary_entry_id` so edits re-embed cleanly. Job status
  moves `pending` → `processing` → `completed`/`failed`, with `attempts` and `error_message`
  columns supporting retry and debugging.

- **Deletion**: `DELETE /diaries/{id}` deletes the entry's Qdrant points synchronously, filtered
  by `diary_entry_id`. This doesn't need embedding compute, so it doesn't go through the async
  job table.

- **Vector store**: a single Qdrant collection, `diary_chunks`. Vector size matches the embedding
  model's dimension (1024 for `multilingual-e5-large`), using Cosine distance. Payload per point:
  `user_id`, `diary_entry_id`, `chunk_index`, `chunk_text`, `entry_date` — payload-indexed on
  `user_id` so every search is filtered to the requesting account, mirroring the app-level
  scoping already used for diary and session data.

- **Chat/RAG request flow** (`POST /conversations/{id}/messages`): embed the user's message via
  Ollama → similarity search in Qdrant filtered to `user_id`, top-k chunks → build a prompt from
  the retrieved chunk text plus the conversation's recent turns → call the Ollama chat model,
  streamed → persist the user message and the assistant reply (storing `cited_diary_entry_ids` on
  the assistant row) → stream tokens to the frontend via SSE so the UI can show incremental
  output while generation is in progress.

- **Scope guarding**: the chat system prompt constrains the model to answer only from retrieved
  diary context or a fixed set of app-help content (Living Genie's features, supported languages,
  etc.), and to refuse anything else with a fixed rejection message. This is handled at the
  prompt level rather than with a separate classifier model or pipeline stage, keeping resource
  usage down and matching the project's minimal-services approach. A lightweight
  pre-classification step is the natural fallback if prompt-level guarding proves too easy to
  work around, but isn't needed to start.

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

`embedding_jobs` table:

| Column           | Type                       | Notes                                         |
|------------------|----------------------------|-------------------------------------------------|
| `id`             | uuid, PK                   |                                                   |
| `diary_entry_id` | uuid, FK → `diary_entries.id` | not null, indexed, cascade-deletes with the entry |
| `status`         | text                       | `pending` / `processing` / `completed` / `failed` |
| `attempts`       | int                        | default `0`, incremented on each processing attempt |
| `error_message`  | text                       | nullable; set when `status` is `failed`          |
| `created_at`     | timestamptz                | system-set on creation                           |
| `updated_at`     | timestamptz                | system-set on every status change                |

`conversations` table:

| Column       | Type                  | Notes                                              |
|--------------|-----------------------|-------------------------------------------------------|
| `id`         | uuid, PK               |                                                        |
| `user_id`    | uuid, FK → `users.id`  | not null, indexed, cascade-deletes with the user       |
| `created_at` | timestamptz            | system-set on creation                                |
| `updated_at` | timestamptz            | bumped on each new message; drives conversation-list ordering |

`messages` table:

| Column                  | Type                       | Notes                                        |
|-------------------------|----------------------------|--------------------------------------------------|
| `id`                    | uuid, PK                   |                                                    |
| `conversation_id`       | uuid, FK → `conversations.id` | not null, indexed, cascade-deletes with the conversation |
| `role`                  | text                       | `user` / `assistant`                              |
| `content`               | text                       | message body                                      |
| `cited_diary_entry_ids` | uuid[]                     | nullable; set only on `assistant` rows            |
| `created_at`            | timestamptz                | system-set on creation                            |

## Containerization

- Separate `Dockerfile` for the frontend and for the backend; the `worker` service reuses the
  backend's build/image with a different command.
- A root-level `docker-compose.yml` wires together: `web`, `web-api`, `postgres` (with a named
  volume so diary data persists across restarts), a second named volume for the backend's
  uploaded-images directory, `ollama` (named volume `ollama_data:/root/.ollama` for pulled
  models), a one-shot `ollama-init` service that runs `ollama pull` for the configured embedding
  and chat models against the `ollama` service and exits once done, `qdrant` (named volume
  `qdrant_data:/qdrant/storage`), and `worker` (no exposed port; depends on `postgres`, `qdrant`,
  and `ollama` all being healthy).
- Configuration via environment variables, e.g. `DATABASE_URL` for the backend's Postgres
  connection, plus `QDRANT_URL`, `OLLAMA_URL`, `OLLAMA_EMBEDDING_MODEL`, and `OLLAMA_CHAT_MODEL`
  for `web-api`/`worker`. Each service owns its own `.env`/`.env.example` (e.g.
  `web-api/.env.example`) rather than a single shared root file; Compose wires each in per-service
  via `env_file:`.

## Repository layout (proposed)

```
web/         React + TypeScript app
web-api/     FastAPI app
docs/        Requirements, architecture, roadmap
```

This layout is not created by documentation alone — it will be established when infrastructure
is initialized.

## Future considerations

- **Future data sources**: the roadmap describes the chatbot as covering "diaries and future data
  sources." v0.2.0 only wires up diary entries, and its naming is intentionally diary-specific
  (`diary_entry_id`, `diary_chunks`) rather than generic (`source_type`/`source_id`) — a
  deliberate choice to avoid designing for a hypothetical second source before one is real.
  Generalizing this naming is expected work once a second data source is actually scoped, not an
  oversight.
