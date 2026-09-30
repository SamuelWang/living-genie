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
embedding) call Ollama and Qdrant directly — neither proxies through the other. Both also send
logs, metrics, and traces to a self-hosted Prometheus/Loki/Tempo/Grafana stack (not shown). See
[Observability](#observability).

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
  (small string set at this scale). The detected/selected locale is persisted to `localStorage`,
  and synced to the account (`PUT /auth/locale`) whenever a signed-in user changes language — see
  [Email verification & password reset](#email-verification--password-reset); a signed-out
  visitor's choice only affects `localStorage`. A `LanguageSwitcher` component in the header
  (`RootLayout`) lets the user override the language at any time.
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
  the frontend and backend must be deployed under the same site. CORS is configured with
  `allow_credentials=True` and an explicit `frontend_origin` (not `*`, which the browser rejects
  for credentialed requests) so the cookie is actually sent/accepted across the frontend/backend
  ports. An account created by `POST /auth/register` is unverified until its emailed one-time code
  is used, and `POST /auth/login` returns `403` for a correct password against an unverified
  account (distinct from the `401` used for wrong credentials) rather than issuing a session.
  `POST /auth/verify-email`
  auto-logs-in on success — issuing a session and setting the cookie exactly as `/auth/login` does
  — since the user has just proven mailbox ownership via the exact browser flow they started.
  `POST /auth/reset-password` does not: it deletes every `sessions` row for that user (there's no
  "current" session yet, since the request itself isn't authenticated) but issues no new one, so
  the resetting browser is redirected to `/login` to sign in with the new password.
  Verification/reset are delivered as a
  manually-entered code rather than a clickable link specifically so no token ever appears in a
  URL — an automated email-security-scanner prefetching every link in the message has nothing to
  consume, unlike a link-based token, which a scanner's GET would burn before the real user ever
  clicks it. See [Email verification & password reset](#email-verification--password-reset) below
  for the full design.
- **API**: REST endpoints for auth:

  | Method | Path                         | Description                                                        |
  |--------|------------------------------|----------------------------------------------------------------------|
  | POST   | `/auth/register`             | Create a new user account; sends a verification email                |
  | POST   | `/auth/login`                | Authenticate; sets the session cookie; `403` if unverified            |
  | POST   | `/auth/logout`                | Ends the session; clears the cookie                                   |
  | POST   | `/auth/resend-verification`  | Resend the verification code (same response whether or not needed)   |
  | POST   | `/auth/verify-email`         | Verify the account from an emailed one-time code, submitted with the account's email; auto-logs-in on success |
  | POST   | `/auth/forgot-password`      | Request a reset code (same response whether or not the email exists)  |
  | POST   | `/auth/reset-password`       | Set a new password from an emailed one-time code, submitted with the account's email; revokes every session, issues no new one |
  | PUT    | `/auth/locale`                | Update the signed-in user's saved language preference                 |

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
  volume (`uploads_data`, separate from the Postgres volume) mounted at `/app/uploads` in the backend
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
    lossless. The stored filename/URL extension is `.webp`; `GET /media/...` serves it like any
    other file, since `FileResponse` infers `Content-Type` from the file suffix.
  - **JPEG sources** stay JPEG rather than being converted to WebP: JPEG is already a lossy format,
    so re-encoding its decoded pixels into a lossless container would preserve the existing
    compression artifacts at a *larger* file size than the compact lossy JPEG encoding — the
    opposite of "smallest possible size." Instead, JPEGs are re-saved with `quality="keep"` (Pillow
    reuses the original quantization tables, so this adds no further lossy degradation) plus
    `optimize=True` for smaller Huffman tables.
  - `ImageOps.exif_transpose()` is applied before stripping EXIF on either path, so the visible
    orientation is preserved even though the metadata itself is dropped for size.
  - Compression applies at upload time only; files already on disk are never re-encoded.

- **Testing**:
  - pytest: `tests/unit/` for pure logic, `tests/integration/` against a real PostgreSQL database
    (`living_genie_test`, provisioned and migrated automatically)
  - No fixed coverage target

### Email verification & password reset

- **Token table**: a single `email_tokens` table represents both a verification code and a reset
  code, discriminated by `purpose` (`"email_verification"` | `"password_reset"`) rather than two
  near-duplicate tables. `id` is an opaque uuid; rows are looked up by `user_id`/`purpose` (backed
  by a composite index on that pair), not by the code itself, since a short human-typed code isn't
  unique enough to double as a lookup key. `code_hash` stores a `hashlib.sha256` hash of the code,
  never the plaintext; `attempts` (default 0) counts wrong submissions; there's no `consumed`
  flag — single-use is enforced by deleting the row on consumption, mirroring `delete_session()`.
  `security.py`'s `create_email_token()`/`invalidate_email_tokens()`/`consume_email_token()` are
  parallel to `create_session()`/`delete_session()`: `create_email_token()` generates an
  `email_code_length`-character code from an alphabet excluding visually ambiguous characters
  (`0`/`O`, `1`/`I`/`L`) and returns the plaintext once, for the email; `consume_email_token()`
  compares via `hmac.compare_digest`, incrementing `attempts` on a mismatch and deleting the row
  once it reaches `email_code_max_attempts` — the same effect as expiry, forcing a resend.
- **Expiry**: verification codes last `email_verification_token_expire_minutes` (1440, 24h), since
  a leaked one only activates an empty new account; reset codes last
  `password_reset_token_expire_minutes` (30), since they grant control of an existing,
  potentially data-bearing account.
- **Reissue invalidates prior codes**: `/auth/resend-verification` and `/auth/forgot-password`
  call `invalidate_email_tokens()` before issuing a new token, so there's never more than one
  valid code per purpose per user.
- **Anti-enumeration**: `/auth/resend-verification` and `/auth/forgot-password` return an
  identical `202` regardless of whether the email is registered (or, for resend, already
  verified) — a no-op internally if not found. `/auth/verify-email` and `/auth/reset-password`
  return the same generic "invalid or expired code" error for a wrong code, an
  expired/already-consumed code, an already-locked-out code, or a nonexistent email — no
  distinguishable failure path.
- **Login resends on unverified**: `/auth/login` against an unverified account returns `403` and,
  subject to the same cooldown as `/auth/resend-verification`, also re-sends the verification
  email as a side effect.
- **No auto-login on reset**: `/auth/verify-email` creates a session and sets the cookie on
  success, exactly like `/auth/login`. `/auth/reset-password` does not — it deletes every
  session for the user but issues no new one; the resetting browser is redirected to `/login` to
  sign in with the new password.
- **Email module**: a flat `web-api/app/email.py` (matching `embeddings.py`/`chunking.py`) built
  on `aiosmtplib`. Provider-agnostic — STARTTLS/auth are driven entirely by settings, and login is
  skipped when `smtp_user` is empty, so the same code path works unauthenticated against Mailpit
  and authenticated against a real relay with no code change. Sends go through FastAPI's
  `BackgroundTasks` and are best-effort — caught and logged, never raised — since
  `/auth/register` and `/auth/forgot-password` must still succeed if SMTP is briefly down. Each
  email is multipart (plain-text + HTML).
- **Localized content**: subject/body strings live in an inline
  `_EMAIL_COPY = {"en": {...}, "zh-Hant": {...}}` dict in `email.py` rather than a general i18n
  framework — the string set is tiny, the same reasoning the frontend applies to its own locale
  JSON. Copy is selected via the target user's `locale` column. The body shows the plaintext code
  and its validity window; it may include a plain convenience link to the app's verify/reset page,
  but the code itself is never embedded in a URL.
- **Locale persistence**: `users.locale` (default `"zh-Hant"`) is set from the frontend's current
  language at registration and kept in sync via `PUT /auth/locale`, called by the language
  switcher whenever a signed-in user changes language. A signed-out visitor's choice still only
  persists to `localStorage`.
- **Resend cooldown**: `email_tokens` rows are deleted on both consume and invalidate, so they
  can't answer "when was the last email actually sent." Two nullable `timestamptz` columns on
  `users` — `last_verification_email_sent_at`/`last_password_reset_email_sent_at` — track that
  instead, set whenever the corresponding email is sent (including registration's initial one).
  Within the configured cooldown, `/auth/resend-verification`/`/auth/forgot-password` are a
  silent no-op — same `202`, no new code, no email — rather than a distinguishable "please wait,"
  since a distinct response would let a caller tell a registered email (which can enter cooldown)
  apart from one that never does.
- **Settings** (`web-api/app/settings.py`/`.env.example`): `smtp_host` (`localhost`), `smtp_port`
  (`1025`, Mailpit's default), `smtp_user`/`smtp_password` (empty), `smtp_from_email`,
  `smtp_from_name`, `smtp_use_tls` (`false`), `email_verification_token_expire_minutes` (1440),
  `password_reset_token_expire_minutes` (30), `resend_verification_cooldown_seconds` (60),
  `password_reset_request_cooldown_seconds` (60), `email_code_length` (8),
  `email_code_max_attempts` (5).

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
  (`task: search result | query: ...` / `title: none | text: ...`) prefixes — see `embed_texts()`
  in `web-api/app/embeddings.py`. `gemma4:e2b-it-qat` (Google) is used for chat: `ollama show`
  confirms native `tools` (required by the tool-calling design below) and `thinking`
  capabilities, and a manual evaluation (per [Ollama model evaluation](ollama-model-evaluation.md))
  found acceptable warm-call latency and fluent bilingual (English/Traditional Chinese) output on
  this project's hardware. Models are pulled on first startup by the one-shot `ollama-init`
  service (`ollama pull` against the `ollama` service, exiting once done).

- **Chunking**: on diary entry or todo create/update (including toggling a todo's `completed`
  flag, since that changes its embedded text), `web-api` enqueues a row in `embedding_jobs` with
  status `pending` rather than embedding inline, keeping the save request fast — see
  [Source-generic indexing](#source-generic-indexing) below.

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

- **Vector store**: a single Qdrant collection, `entry_chunks`. Vector size matches the embedding model's
  dimension (768 for `embeddinggemma:300m`), using Cosine distance. Payload-indexed on `user_id` so
  every search is filtered to the requesting account, mirroring the app-level scoping already used
  for diary, todo, and session data. Search takes a candidate pool of
  `RETRIEVAL_CANDIDATE_POOL_SIZE` nearest points and re-ranks them by blending cosine similarity
  with a recency bonus (`RETRIEVAL_RECENCY_WEIGHT`, exponential decay with half-life
  `RETRIEVAL_RECENCY_HALF_LIFE_DAYS`) before keeping the top `RETRIEVAL_TOP_K`. See
  [Source-generic indexing](#source-generic-indexing) for the payload shape.

- **Chat/RAG request flow** (`POST /conversations/{id}/messages`): persist the user message →
  if the conversation has a `pending_action` that this message confirms, execute it directly (see
  [Tool-calling](#tool-calling-managing-todos-through-chat)); otherwise embed the message via
  Ollama → similarity search in Qdrant filtered to `user_id` → build a prompt from the retrieved
  chunk text plus the last `CHAT_CONTEXT_TURNS` turns → run the tool-calling loop against the
  Ollama chat model → stream the final reply to the frontend via SSE (a `references` event
  first, then tokens) → persist the assistant reply with its source references (see
  [Data model](#data-model)).

- **Scope guarding**: the chat system prompt constrains the model to answer only from retrieved
  context (diary entries or todos) or a fixed set of app-help content (Living Genie's features,
  supported languages, etc.), and to refuse anything else with a fixed rejection message. This is
  handled at the prompt level rather than with a separate classifier model or pipeline stage,
  keeping resource usage down and matching the project's minimal-services approach.

### Source-generic indexing

The indexing/retrieval pipeline (`embedding_jobs`, `vector_store.py`, the worker, and
`message_references`) is shared across data sources; diary entries and todos differ only in
`source_type`:

- **`embedding_jobs`** identifies its source by a `source_type` (`"diary_entry"` | `"todo"`) plus
  `source_id` (uuid) pair — plain columns, not a per-type FK, so a new data source needs no schema
  change. Without an FK there's no DB cascade-delete; none is needed, since Qdrant cleanup happens
  explicitly on delete (above), the worker treats a missing source row as a skip, and a leftover
  `completed` job row is inert.
- **`entry_chunks` payload** per point: `user_id`, `source_type`, `source_id`, `chunk_index`,
  `chunk_text`, and `date` (feeds recency re-ranking) — a diary entry's `entry_date`; a todo's
  `due_date` if set, else its `created_at` date. Search returns a mixed ranked list of diary and
  todo chunks.
- **Worker** dispatches on `job.source_type`: diary jobs chunk `DiaryEntry.content`; todo jobs
  chunk a composed string of title, description, and a `Status: done`/`Status: pending` line, so
  retrieval can answer "have I already done X?"-style questions.
- **`message_references`** (see [Data model](#data-model)) uses the same `source_type`/`source_id`
  shape for both retrieval citations and action references (a todo a chat mutation affected); the
  conversation UI renders a chip linking to `/diaries/{id}` or `/todos/{id}` accordingly.

The domain tables (`diary_entries`, `todos`) and their CRUD routers stay source-specific.

### Tool-calling: managing todos through chat

**Reads** ("what's due this week?", "have I bought milk?") go through the retrieval pipeline
above, like diary Q&A — there's no lookup tool. **Tool-calling is reserved for mutations**: four
tools (`web-api/app/todo_tools.py`) are passed to the Ollama chat call, each scoped server-side to
`current_user.id` and never accepting a user id from the model:

- `create_todo(title, description?, due_date?)`
- `update_todo(title, due_date?, new_title?, new_description?, new_due_date?, user_confirmed)`
- `complete_todo(title, due_date?, user_confirmed)`
- `delete_todo(title, due_date?, user_confirmed)`

Todos are identified **by title** rather than by id, since the model has no reliable way to track
opaque ids across turns: a case-insensitive exact match wins; otherwise the closest fuzzy match
(`difflib` similarity ≥ 0.6, and at least 0.15 ahead of the runner-up) is used. The optional
`due_date` narrows candidates first. A not-found or ambiguous title returns an `ok: false` result
whose message asks for more detail.

**Confirmation**: `update_todo`, `complete_todo`, and `delete_todo` require `user_confirmed:
bool`; `create_todo` doesn't. The backend never executes a confirming tool unless
`user_confirmed=true` — otherwise the result is `needs_confirmation`, telling the model to ask
first, and the proposed call (minus `user_confirmed`) is stored on `conversations.pending_action`.
On the next message, if a pending action exists, a separate low-temperature structured-output call
(`pending_action_is_confirmed()`) judges whether the message confirms it; if so, the action is
executed directly with `user_confirmed=true` and its result message is the reply, bypassing the
LLM. Any other turn clears `pending_action`. There is no dedicated confirm/cancel UI control.

**Multi-turn loop** (`run_chat_with_tools()` in `web-api/app/chat.py`): the model is called with
`tools=[...]` at `OLLAMA_TOOL_TEMPERATURE`; each returned tool call is executed and an `assistant`
(tool_calls) message plus a `tool` (result) message are appended before calling again, up to
`CHAT_TOOL_MAX_ITERATIONS` (default 4). Once a response has no tool calls, a final `stream=True`
call at `OLLAMA_CHAT_TEMPERATURE` streams the reply. If a confirmed action failed and nothing was
mutated, the failure messages are returned verbatim instead, so the model can't narrate a success
that didn't happen. A successful mutation adds a `message_references` row for the affected todo.
`build_system_prompt()` covers todos as an in-scope topic alongside diary excerpts and app help,
plus the confirm-before-acting instruction.

**Known limitation**: the `user_confirmed` gate is mechanical, so no todo is mutated without
confirmation; but the model can occasionally skip asking and falsely claim an action already
succeeded. `OLLAMA_CHAT_TEMPERATURE=0.3` (`.env.example`) measurably reduces this (0/8 vs. 1/5
trials at 1.0) without eliminating it.

## Data model

`users` table:

| Column              | Type              | Notes                                   |
|---------------------|-------------------|--------------------------------------------|
| `id`                | uuid, PK          |                                             |
| `email`             | text              | unique, not null                           |
| `hashed_password`   | text              | not null, never exposed via API            |
| `email_verified_at` | timestamptz       | nullable; NULL = not verified              |
| `locale`            | text              | not null, default `"zh-Hant"`              |
| `last_verification_email_sent_at` | timestamptz | nullable; set whenever a verification email is sent, enforces the resend cooldown |
| `last_password_reset_email_sent_at` | timestamptz | nullable; set whenever a reset email is sent, enforces the resend cooldown |
| `created_at`        | timestamptz       | system-set on creation                     |

`diary_entries` table:

| Column       | Type                  | Notes                                   |
|--------------|-----------------------|------------------------------------------|
| `id`         | uuid, PK               |                                          |
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

`email_tokens` table (see
[Email verification & password reset](#email-verification--password-reset) for why `purpose` is
shaped this way):

| Column       | Type                  | Notes                                              |
|--------------|-----------------------|---------------------------------------------------------|
| `id`         | uuid, PK              | opaque row id; not the code itself |
| `user_id`    | uuid, FK → `users.id` | not null, indexed, cascade-deletes with the user          |
| `purpose`    | text                  | `email_verification` / `password_reset`; not null         |
| `code_hash`  | text                  | not null; `hashlib.sha256` hash of the one-time code, never stored in plaintext |
| `attempts`   | int                   | not null, default `0`; incremented on each incorrect code submission |
| `created_at` | timestamptz           | system-set on creation                                     |
| `expires_at` | timestamptz           | code expiry; checked on consumption                        |

`embedding_jobs` table (see [Source-generic indexing](#source-generic-indexing) for why
`source_type`/`source_id` is shaped this way):

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
| `pending_action` | jsonb              | nullable; a gated tool call (`name`, `arguments`) awaiting the user's confirmation — see [Tool-calling](#tool-calling-managing-todos-through-chat) |

`messages` table (assistant-message source references live in the separate `message_references`
table below, not a column here):

| Column                  | Type                       | Notes                                        |
|-------------------------|----------------------------|--------------------------------------------------|
| `id`                    | uuid, PK                   |                                                    |
| `conversation_id`       | uuid, FK → `conversations.id` | not null, indexed, cascade-deletes with the conversation |
| `role`                  | text                       | `user` / `assistant`                              |
| `content`               | text                       | message body                                      |
| `created_at`            | timestamptz                | system-set on creation                            |

`message_references` table — an assistant message's retrieval citations and action references,
using the same `source_type`/`source_id` shape as `embedding_jobs`; unlike `embedding_jobs`, it
cascade-deletes with its message, since the two share one lifecycle:

| Column        | Type                  | Notes                                             |
|---------------|-----------------------|--------------------------------------------------------|
| `id`          | uuid, PK              |                                                          |
| `message_id`  | uuid, FK → `messages.id` | not null, indexed, cascade-deletes with the message |
| `source_type` | text                  | `diary_entry` / `todo`; not null                         |
| `source_id`   | uuid                  | not null, indexed                                        |

## Observability

`web-api` and `worker` emit logs, metrics, and traces to a self-hosted stack in the same Compose
project; nothing leaves the host.

```
web-api ─┐  OTLP gRPC (traces + logs)            ┌─> tempo  (traces)
         ├──────────────────────────> alloy ─────┤
worker  ─┘                                        └─> loki   (logs, via /otlp)
web-api:8000/metrics, worker:9101/metrics <── prometheus (scrape, 15s)
                          grafana ──> prometheus / loki / tempo
```

- **Bootstrap** (`web-api/app/observability.py`): each process calls
  `configure_tracing(service_name)` then `configure_logging()` at startup — `app/main.py` with
  `"web-api"`, `app/worker.py` with `"worker"`. Call sites log via `get_logger(__name__)` (a
  `structlog` logger).
- **Logging**: `structlog` and stdlib `logging` share one root-logger setup at INFO level, with
  two handlers:
  - stdout: one JSON object per line with `timestamp`, `level`, `logger`, `event`, plus
    `trace_id`/`span_id` when a span is active.
  - OTLP: an OTel `LoggingHandler` → `BatchLogRecordProcessor(OTLPLogExporter)` to
    `OTEL_EXPORTER_OTLP_ENDPOINT`, sharing the tracer provider's `service.name` resource.

  uvicorn's loggers are routed to the root handlers, and `uvicorn.access` lines for `/health` and
  `/metrics` are dropped. `configure_logging(export=False)` skips the OTLP handler; it's used by
  `alembic/env.py` (short-lived CLI runs).
- **Tracing**: a `TracerProvider` with `service.name` (`web-api`/`worker`), a
  `TraceIdRatioBased(OTEL_TRACES_SAMPLER_RATIO)` sampler, and a `BatchSpanProcessor` exporting
  over OTLP gRPC to `OTEL_EXPORTER_OTLP_ENDPOINT`. Auto-instrumentation: `FastAPIInstrumentor`
  (`web-api`), `SQLAlchemyInstrumentor` and `HTTPXClientInstrumentor` (both; covers the Ollama
  and Qdrant clients). Custom spans:

  | Span                | Service   | Attributes                                                         |
  |---------------------|-----------|---------------------------------------------------------------------|
  | `chat.embed_query`  | `web-api` |                                                                      |
  | `chat.qdrant_search`| `web-api` |                                                                      |
  | `chat.build_prompt` | `web-api` |                                                                      |
  | `chat.ollama_call`  | `web-api` | `chat.iteration` (1-based tool-loop iteration)                       |
  | `chat.tool_call`    | `web-api` | `tool.name`, `tool.user_confirmed`, `tool.gated` (held for confirmation) |
  | `job.process`       | `worker`  | root span per claimed job: `job.id`, `source_type`, `source_id`, `job.status` |
  | `job.chunk`         | `worker`  | `source_type`, `source_id`                                          |
  | `job.embed_chunks`  | `worker`  | `source_type`, `source_id`, `chunk_count`                           |
  | `job.qdrant_upsert` | `worker`  | `source_type`, `source_id`                                          |

  `job.*` stage spans record an exception and `ERROR` status when the stage raises, as does
  `job.process`. The worker's idle polling query runs under `suppress_instrumentation()` and
  exports nothing.
- **Metrics**:
  - `web-api`: `GET /metrics` (unauthenticated) via `prometheus-fastapi-instrumentator` —
    `http_requests_total`, `http_request_duration_seconds`,
    `http_request_duration_highr_seconds` (per-route metrics labelled by `handler`).
  - `worker`: `prometheus_client.start_http_server(WORKER_METRICS_PORT)`, exposed on the Compose
    network only.
  - Custom metrics:

    | Metric                                     | Type      | Labels                     | Service   |
    |--------------------------------------------|-----------|----------------------------|-----------|
    | `living_genie_tool_calls_total`            | counter   | `tool_name`, `user_confirmed` | `web-api` |
    | `living_genie_rag_retrieval_seconds`       | histogram | —                          | `web-api` |
    | `living_genie_worker_jobs_total`           | counter   | `source_type`, `status`    | `worker`  |
    | `living_genie_worker_job_duration_seconds` | histogram | `source_type`              | `worker`  |

- **Collection** (config at the repo root):
  - `alloy/config.alloy`: `otelcol.receiver.otlp` (gRPC `:4317`) → `otelcol.processor.batch` →
    traces to `tempo:4317`, logs to `http://loki:3100/otlp`.
  - `loki/loki-config.yaml`: native OTLP ingestion. `service.name` is indexed as the
    `service_name` label, and `trace_id`/`span_id` are stored as structured metadata.
  - `tempo/tempo.yaml`: OTLP gRPC receiver, single-binary mode.
  - `prometheus/prometheus.yml`: scrapes `web-api:8000` and `worker:9101` every 15s.
- **Grafana** (`grafana/`): provisioned datasources Prometheus (default), Loki, and Tempo (uids
  `prometheus`/`loki`/`tempo`). Tempo's `tracesToLogsV2` opens
  `{service_name="<span's service.name>"} | trace_id="<trace id>"` in Loki ("Related logs" on a
  span). Loki's `trace_id` derived field links back to Tempo. The file-provisioned "Living Genie
  overview" dashboard (folder "Living Genie", `grafana/dashboards/overview.json`) has three rows:
  - web-api: request rate by route, 5xx share, p50/p95 latency
  - Chat / RAG: tool calls by `tool_name`/`user_confirmed`, RAG retrieval p50/p95
  - Worker: jobs by `source_type`/`status`, job duration p95 by `source_type`
- **Settings** (`web-api/app/settings.py`/`.env.example`):

  | Variable                      | Default              | Consumed by                                  |
  |-------------------------------|----------------------|----------------------------------------------|
  | `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://alloy:4317`  | `web-api`, `worker` (traces and logs)        |
  | `OTEL_TRACES_SAMPLER_RATIO`   | `1.0`                | `web-api`, `worker`                          |
  | `WORKER_METRICS_PORT`         | `9101`               | `worker` (Prometheus target is hardcoded to match) |
  | `PROMETHEUS_RETENTION`        | `15d`                | `prometheus` `--storage.tsdb.retention.time` |
  | `LOKI_RETENTION_PERIOD`       | `168h`               | `loki` `limits_config.retention_period`      |
  | `TEMPO_RETENTION`             | `336h`               | `tempo` `block_retention`                    |

  The retention variables are read from `web-api/.env` by the Compose services (via `env_file`
  and env expansion), not by application code.

## Containerization

- Separate `Dockerfile` for the frontend and for the backend; the `worker` service reuses the
  backend's build/image with a different command.
- A root-level `docker-compose.yaml` wires together: `web`, `web-api`, `postgres` (with a named
  volume so diary data persists across restarts), a second named volume for the backend's
  uploaded-images directory, `ollama` (named volume `ollama_data:/root/.ollama` for pulled
  models), a one-shot `ollama-init` service that runs `ollama pull` for the configured embedding
  and chat models against the `ollama` service and exits once done, `qdrant` (named volume
  `qdrant_data:/qdrant/storage`), and `worker` (metrics port `9101` exposed to the Compose network
  only; depends on `postgres`, `qdrant`, and `ollama` all being healthy). `web-api` and `worker`
  also depend on `alloy` being started.
- Observability services (see [Observability](#observability)): `prometheus`
  (`prom/prometheus:v3.15.0`), `loki` (`grafana/loki:3.7.8`), `tempo` (`grafana/tempo:3.0.3`),
  `alloy` (`grafana/alloy:v1.20.0`), and `grafana` (`grafana/grafana:13.2.2`). Each has its own
  named volume, and config files are mounted read-only. Only `grafana` (`3000`) and `prometheus`
  (`9090`) are published to the host. Grafana's admin login comes from `GRAFANA_ADMIN_USER`/
  `GRAFANA_ADMIN_PASSWORD` in the root `.env` (default `admin`/`admin`), and usage reporting is
  disabled in Loki, Tempo, and Grafana.
- Configuration via environment variables. `web-api/.env` (shared by `web-api`, `worker`,
  `ollama-init`, and the `prometheus`/`loki`/`tempo` retention flags) holds application settings.
  Compose overrides the in-network `DATABASE_URL`, `QDRANT_URL`, and `OLLAMA_URL`. The root `.env`
  holds Compose-level values: `POSTGRES_*` and `GRAFANA_ADMIN_*`. `web/.env` holds the frontend's.
  Each has a matching `.env.example`.
- **Local dev only**: `docker-compose.dev.yaml` adds a `mailpit` container (SMTP catcher + web
  UI, `axllent/mailpit`, no persistent volume) so verification/reset emails can be viewed locally
  without a real SMTP provider account; `web-api`'s dev environment points `SMTP_HOST` at it. It
  also switches `web-api`, `worker`, and `web` to their `dev` build targets with source
  bind-mounted for hot reload. In the base `docker-compose.yaml`, SMTP comes from `web-api/.env`
  like any other setting.

## Repository layout

```
web/         React + TypeScript app
web-api/     FastAPI app and indexing worker (app/worker.py)
docs/        Requirements, execution plans, architecture, roadmap, release notes
prometheus/  Prometheus scrape config
loki/        Loki config
tempo/       Tempo config
alloy/       Grafana Alloy (OTLP collector) config
grafana/     Grafana provisioning (datasources, dashboard provider) and dashboards
```

## Future considerations

- **Future data sources**: the roadmap describes the chatbot as covering "diaries and future data
  sources." Because the indexing/retrieval pipeline is source-generic (see
  [Source-generic indexing](#source-generic-indexing)), a new data source needs a new
  `source_type` value, its own domain table and CRUD router, and a worker branch composing its
  chunk text. It needs no schema change to `embedding_jobs`, `entry_chunks`, or
  `message_references`.
