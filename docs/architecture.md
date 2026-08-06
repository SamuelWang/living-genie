# Architecture

This document describes Living Genie's technical architecture. It is stack-level rather than
phase-specific: it describes the system as it currently stands, and is expected to keep growing
(not be rewritten) as new capabilities are added. See [roadmap.md](roadmap.md) for the phase
breakdown and the [requirements](requirements/) docs for phase-by-phase functional detail.

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
  only — no backend involvement, since the preference isn't synced to the account. A
  language-switcher component (e.g. in the nav) lets the user override the language at any time.
- **Testing**:
  - Vitest + React Testing Library for unit/component tests
  - Playwright for integration/e2e tests of key flows (diary CRUD end-to-end through the UI)
  - No fixed coverage target

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
  todo, upload, and media endpoints require a valid session and operate only on the authenticated
  user's own data. `POST /auth/logout` deletes the session server-side, which a stateless token couldn't
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

  Todo CRUD, following the exact same pattern as diary CRUD:

  | Method | Path             | Description                                     |
  |--------|------------------|----------------------------------------------------|
  | POST   | `/todos`         | Create a todo                                       |
  | GET    | `/todos`         | List todos (optional `?completed=` filter)          |
  | GET    | `/todos/{id}`    | Get a single todo                                   |
  | PUT    | `/todos/{id}`    | Update a todo, including toggling `completed`       |
  | DELETE | `/todos/{id}`    | Delete a todo                                       |

  There's no dedicated "complete" endpoint — `PUT` (all fields optional, only supplied fields are
  applied, matching `DiaryEntryUpdate`) covers toggling `completed` from the UI.

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
  consistent with keeping uploads minimal.

- **Image compression**: uploads are decoded and re-encoded with `Pillow` before being written to
  disk, rather than a raw byte-copy. Decoding as an image is also the validation step — a
  non-image upload fails with a 400 instead of being stored verbatim. The re-encoding is chosen
  per source format rather than one blanket target format, since "smallest possible size
  losslessly" means something different for each:
  - **Already-lossless sources (PNG, BMP, TIFF, etc.)** are converted to **WebP, lossless mode**
    (`Image.save(..., "WEBP", lossless=True)`). WebP's lossless codec is consistently smaller than
    PNG's for identical pixels, so it beats simply re-optimizing PNG while staying pixel-for-pixel
    lossless. The stored filename/URL extension becomes `.webp`; `GET /media/...` needs no code
    change, since `FileResponse` infers `Content-Type` from the file suffix and `image/webp` is a
    registered mimetype.
  - **JPEG sources** stay JPEG rather than being converted to WebP: JPEG is already a lossy format,
    so re-encoding its decoded pixels into a lossless container would preserve the existing
    compression artifacts at a *larger* file size than the compact lossy JPEG encoding — the
    opposite of "smallest possible size." Instead, JPEGs are re-saved with `quality="keep"` (Pillow
    reuses the original quantization tables, so this adds no further lossy degradation) plus
    `optimize=True` for smaller Huffman tables.
  - `ImageOps.exif_transpose()` is applied before stripping EXIF on either path, so the visible
    orientation is preserved even though the metadata itself is dropped for size.
  - Compression applies at upload time only; it does not retroactively touch files already on
    disk — no backfill/migration.

- **Testing**:
  - Unit tests for business logic
  - Integration tests run against a real/test PostgreSQL instance (e.g. pytest)
  - No fixed coverage target

## AI / RAG pipeline

- **Local inference**: an `ollama` service serves both embedding and chat generation; model tags
  are configurable via `OLLAMA_EMBEDDING_MODEL` (default `embeddinggemma:300m`) and
  `OLLAMA_CHAT_MODEL` (default `gemma4:e2b-it-qat`) environment variables. Both are non-China-origin,
  open-weight models that run CPU-only if needed, though interactive-latency chat generation
  benefits substantially from GPU acceleration — the `ollama` service requests an NVIDIA GPU via
  Docker Compose's `deploy.resources.reservations.devices` (falls back to CPU automatically if
  none is available on the host). `embeddinggemma:300m` (Google) is used for embeddings: small
  (~300M params) and explicitly multilingual-trained (100+ languages, including Chinese), which
  matters since diary content is expected to be mostly Traditional Chinese; it's pulled from
  Ollama's official library. Its query/document prompts follow EmbeddingGemma's own convention
  (`task: search result | query: ...` / `title: none | text: ...`) prefixes — 
  see `embed_texts()` in `web-api/app/embeddings.py`. `gemma3:4b` (Google) was the original chat
  pin, chosen for license permissiveness and multilingual coverage after `gemma2:9b` proved too
  large to load in reasonable time on modest/CPU-only hardware — but `gemma3:4b` doesn't support
  Ollama's `tools` capability, which the tool-calling design below depends on. `gemma4:e2b-it-qat`
  replaces it: `ollama show gemma4:e2b-it-qat` confirms native `tools` and `thinking` capabilities,
  and a manual evaluation (per
  [Ollama model evaluation](ollama-model-evaluation.md)) found acceptable warm-call latency and
  fluent bilingual (English/Traditional Chinese) output on this project's hardware. Models are
  pulled on first startup via a one-shot init step (a short-lived service running `ollama pull`
  against the `ollama` service, exiting once done).

- **Chunking**: on diary entry or todo create/update (including toggling a todo's `completed`
  flag, since that changes its embedded text), `web-api` enqueues a row in `embedding_jobs` with
  status `pending` rather than embedding inline, keeping the save request fast — see
  [Generalizing the indexing pipeline for todos](#generalizing-the-indexing-pipeline-for-todos)
  below.

- **Indexing worker**: a dedicated `worker` process (same build as `web-api`, different command)
  polls `embedding_jobs` for pending rows using `SELECT ... FOR UPDATE SKIP LOCKED` (safe under
  concurrent polling), splits the source content into paragraph-aware chunks with overlap, embeds
  each chunk via Ollama, and upserts the resulting vectors into Qdrant — replacing any prior points
  for that source so edits re-embed cleanly. Job status moves `pending` → `processing` →
  `completed`/`failed`, with `attempts` and `error_message` columns supporting retry and debugging.

- **Deletion**: `DELETE /diaries/{id}` and `DELETE /todos/{id}` delete the source's Qdrant points
  synchronously, before the Postgres row is deleted — a correctness guarantee (the delete aborts
  if vector cleanup fails), not best-effort cleanup. This doesn't need embedding compute, so it
  doesn't go through the async job table.

- **Vector store**: a single Qdrant collection. Vector size matches the embedding model's
  dimension (768 for `embeddinggemma:300m`), using Cosine distance. Payload-indexed on `user_id` so
  every search is filtered to the requesting account, mirroring the app-level scoping already used
  for diary, todo, and session data. See below for the exact payload shape.

- **Chat/RAG request flow** (`POST /conversations/{id}/messages`): embed the user's message via
  Ollama → similarity search in Qdrant filtered to `user_id`, top-k chunks → build a prompt from
  the retrieved chunk text plus the conversation's recent turns → call the Ollama chat model,
  passing todo-mutating tools alongside it (see
  [Tool-calling: managing todos through chat](#tool-calling-managing-todos-through-chat) below) →
  streamed → persist the user message and the assistant reply (recording which sources it drew
  from — see [Data model](#data-model)) → stream tokens to the frontend via SSE so the UI can show
  incremental output while generation is in progress.

- **Scope guarding**: the chat system prompt constrains the model to answer only from retrieved
  context (diary entries or todos) or a fixed set of app-help content (Living Genie's features,
  supported languages, etc.), and to refuse anything else with a fixed rejection message. This is
  handled at the prompt level rather than with a separate classifier model or pipeline stage,
  keeping resource usage down and matching the project's minimal-services approach. A lightweight
  pre-classification step is the natural fallback if prompt-level guarding proves too easy to
  work around, but isn't needed to start.

### Generalizing the indexing pipeline for todos

The indexing/retrieval pipeline (`embedding_jobs`, `vector_store.py`, the worker, and the
assistant-message reference mechanism) is generic across data sources rather than diary-specific,
so that diary entries and todos share one mechanism instead of each needing its own copy — see
[Future considerations](#future-considerations) for why this generality matters going forward:

- **`embedding_jobs`**: `diary_entry_id` is replaced by a generic `source_type` (`"diary_entry"` |
  `"todo"`) plus `source_id` (uuid) pair — plain, unconstrained columns rather than a per-type FK.
  This is the `source_type`/`source_id` shape the earlier "Future considerations" note already
  anticipated, and it scales to any future third data source with no further schema change (a
  nullable FK column per type, by contrast, would need a migration and a wider/sparser table every
  time a source is added). This does mean the table loses DB-enforced cascade-delete, but the
  codebase never actually relied on that here: Qdrant isn't Postgres, so cascade never covered the
  vector-store side of cleanup anyway (the worker/deletion path already handles that explicitly,
  above), and the worker already tolerates a since-deleted source row as an ordinary race
  condition (`entry is None` → log and skip). A deleted diary entry or todo can leave a harmlessly
  inert `embedding_jobs` row behind — the worker only ever acts on `pending` rows, and by the time
  a delete happens any indexing job for that content has long since completed — the same
  "no orphan cleanup required" tolerance the project already accepts for uploaded images.
- **Vector store collection**: renamed `diary_chunks` → **`entry_chunks`**. Payload per point:
  `user_id`, `source_type`, `source_id`, `chunk_index`, `chunk_text`, and a generalized `date`
  field (renamed from `entry_date`) feeding the existing recency-rescoring math (unchanged logic —
  exponential decay blended with cosine similarity) — for a diary entry this is its `entry_date`;
  for a todo it's `due_date` if set, else the todo's `created_at` date, so every point has a usable
  recency signal regardless of source. `search()`'s shape and `user_id`-only filter are unchanged;
  it now naturally returns a mixed ranked list of diary and todo chunks for a given query.
- **Worker**: dispatches on `job.source_type` — diary jobs chunk `DiaryEntry.content` exactly as
  before; todo jobs chunk a composed string of the todo's title, description, and a completion
  status line (e.g. `"Status: done"` / `"Status: pending"`), so retrieval can answer
  "have I already done X?"-style questions.
- **Assistant message references**: `messages.cited_diary_entry_ids` is replaced by a proper child
  table, `message_references`, using the same `source_type`/`source_id` shape rather than a
  diary-specific array column or a JSON blob — see [Data model](#data-model). This single
  mechanism covers both retrieval citations (which diary/todo chunks grounded an answer) and
  action references (which todo a chat-driven mutation affected), and the conversation UI renders
  a chip linking to `/diaries/{id}` or `/todos/{id}` depending on `source_type`.

What deliberately stays source-specific: the domain tables themselves (`diary_entries`, `todos`)
and their own CRUD routers, since those are genuinely distinct business entities, not shared
infrastructure — only the cross-cutting indexing/retrieval/reference machinery is generalized.

### Tool-calling: managing todos through chat

Genie's existing single chat endpoint is extended, not replaced, and not split into a separate
"todo mode." **Reads** ("what's due this week?", "have I bought milk?") go through the retrieval
pipeline described above, exactly like diary Q&A — there's no dedicated lookup tool for todos.
**Tool-calling is reserved for mutations**: four tools are passed to the Ollama chat call
(`ollama>=0.6.2`'s `Client.chat()` already supports a `tools` parameter, unused until now), each
implicitly scoped server-side to `current_user.id` and never accepting a user id as a
model-supplied parameter:

- `create_todo(title, description?, due_date?)`
- `update_todo(title, ...fields to change, user_confirmed)`
- `complete_todo(title, user_confirmed)`
- `delete_todo(title, user_confirmed)`

Todos are identified to these tools **by title** (case-insensitive match, scoped to the user)
rather than by id — retrieval already surfaces todo titles naturally in conversation, but the
model has no reliable way to track opaque ids across turns, so requiring one would be brittle. An
ambiguous (multiple-match) or not-found title comes back as an ordinary tool result for the model
to resolve conversationally (e.g. asking the user which one they meant), rather than the backend
guessing.

**Confirmation**: `update_todo`, `complete_todo`, and `delete_todo` each require a
`user_confirmed: bool` parameter in their tool schema; `create_todo` doesn't, since creating isn't
destructive. The backend never executes one of the three confirming tools unless
`user_confirmed=true` is present on the call — if it's missing or `false`, the tool result simply
tells the model to ask the user first instead of acting. This mirrors the existing prompt-level
scope-guarding philosophy above (a system-prompt instruction, not a separate classifier or
state machine) while still giving the backend a mechanical gate rather than trusting the model's
prose alone. There is no dedicated confirm/cancel UI control — confirmation happens as an ordinary
conversational turn, the same way any other reply does.

**Multi-turn loop**: the single `client.chat(...)` call becomes a loop. The model is called with
`tools=[...]`; if the response includes `message.tool_calls`, each is executed against the
corresponding function above, and an `assistant` (tool_calls) message plus a `tool` (result)
message are appended before calling again — capped at a small number of iterations (e.g. 4) to
guard against a runaway loop. Once a response comes back with no tool calls, a final call is made
with `stream=True` to stream the natural-language reply to the client exactly as today. A
successful mutation adds a `message_references` row for the affected todo, so the reply carries a
clickable link the user can use to quickly verify what happened.

`build_system_prompt()` gains todos as a third in-scope topic (alongside diary excerpts and
app-help content) plus the confirm-before-acting instruction above.

**Resolved risk, with a residual caveat**: whether the chat model reliably supports and follows
Ollama's tool-calling conventions — including the confirm-before-acting instruction — was an open,
unverified risk for `gemma3:4b`, which doesn't support Ollama's `tools` capability at all.
`OLLAMA_CHAT_MODEL` was re-pinned to `gemma4:e2b-it-qat`, which `ollama show` confirms natively
supports both `tools` and `thinking`. Live end-to-end testing (see
[execution plan, Section 10](execution/v0.3.0.md)) found the mechanical `user_confirmed` gate
itself is sound — no todo was ever mutated without prior confirmation — but at the model card's
generically recommended sampling temperature (1.0), the assistant would sometimes skip asking for
confirmation and reply with a flat, false claim that an action had already succeeded. Lowering
`OLLAMA_CHAT_TEMPERATURE` to 0.3 measurably reduced this in testing (0/8 vs. 1/5 trials), but did
not mathematically guarantee it can't recur — this is a UX/trust risk (a misleading reply), not a
data-safety one, since no unconfirmed mutation can occur regardless. Worth continued monitoring in
real usage.

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

`todos` table:

| Column        | Type                  | Notes                                             |
|---------------|-----------------------|--------------------------------------------------------|
| `id`          | uuid, PK              |                                                          |
| `user_id`     | uuid, FK → `users.id` | not null, indexed, cascade-deletes with the user        |
| `title`       | text                  | not null                                                 |
| `description` | text                  | nullable                                                 |
| `due_date`    | date                  | nullable                                                 |
| `completed`   | boolean               | not null, default `false`                                |
| `created_at`  | timestamptz           | system-set on creation                                   |
| `updated_at`  | timestamptz           | system-set on every update                               |

`sessions` table:

| Column       | Type                  | Notes                                    |
|--------------|-----------------------|---------------------------------------------|
| `id`         | text, PK              | opaque random token, stored in the session cookie |
| `user_id`    | uuid, FK → `users.id`  | not null, indexed, cascade-deletes with the user |
| `created_at` | timestamptz            | system-set on creation                      |
| `expires_at` | timestamptz            | session expiry; checked on every request     |

`embedding_jobs` table (see
[Generalizing the indexing pipeline for todos](#generalizing-the-indexing-pipeline-for-todos) for
why `source_type`/`source_id` is shaped this way):

| Column          | Type        | Notes                                                |
|-----------------|-------------|----------------------------------------------------------|
| `id`            | uuid, PK    |                                                            |
| `source_type`   | text        | `diary_entry` / `todo`; not null                          |
| `source_id`     | uuid        | not null, indexed; id of the `diary_entries` or `todos` row — not FK-constrained (see rationale above), so a deleted source can leave a harmless, inert orphaned row |
| `status`        | text        | `pending` / `processing` / `completed` / `failed`         |
| `attempts`      | int         | default `0`, incremented on each processing attempt      |
| `error_message` | text        | nullable; set when `status` is `failed`                   |
| `created_at`    | timestamptz | system-set on creation                                    |
| `updated_at`    | timestamptz | system-set on every status change                          |

`conversations` table:

| Column       | Type                  | Notes                                              |
|--------------|-----------------------|-------------------------------------------------------|
| `id`         | uuid, PK               |                                                        |
| `user_id`    | uuid, FK → `users.id`  | not null, indexed, cascade-deletes with the user       |
| `created_at` | timestamptz            | system-set on creation                                |
| `updated_at` | timestamptz            | bumped on each new message; drives conversation-list ordering |

`messages` table (assistant-message source references live in the separate `message_references`
table below, not a column here):

| Column                  | Type                       | Notes                                        |
|-------------------------|----------------------------|--------------------------------------------------|
| `id`                    | uuid, PK                   |                                                    |
| `conversation_id`       | uuid, FK → `conversations.id` | not null, indexed, cascade-deletes with the conversation |
| `role`                  | text                       | `user` / `assistant`                              |
| `content`               | text                       | message body                                      |
| `created_at`            | timestamptz                | system-set on creation                            |

`message_references` table — a proper child table rather than a diary-only array column or a JSON
blob (the schema has no JSON columns elsewhere), reusing the same `source_type`/`source_id` shape
as `embedding_jobs`: covers both retrieval
citations (a diary/todo chunk an answer was grounded in) and action references (a todo a chat
mutation affected) with one mechanism, and cascade-deletes with its message unlike
`embedding_jobs`'s reference, since a message and its references genuinely share one lifecycle:

| Column        | Type                  | Notes                                             |
|---------------|-----------------------|--------------------------------------------------------|
| `id`          | uuid, PK              |                                                          |
| `message_id`  | uuid, FK → `messages.id` | not null, indexed, cascade-deletes with the message |
| `source_type` | text                  | `diary_entry` / `todo`; not null                         |
| `source_id`   | uuid                  | not null, indexed                                        |

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
  sources." Diary entries and todos are both wired up today, and the indexing/retrieval pipeline —
  `embedding_jobs`, the Qdrant collection/payload (`entry_chunks`, `source_type`/`source_id`), the
  worker, and the `message_references` table — is source-type-generic rather than tied to either
  one, so a future third data source should need no further schema change to those shared pieces,
  just a new `source_type` value and a router for the new domain entity. What stays source-specific, deliberately,
  are the domain tables themselves (`diary_entries`, `todos`) and their own CRUD routers, since
  those are genuinely distinct business entities, not shared infrastructure.
