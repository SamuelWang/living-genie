# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-07-28

### Added

- Genie, a retrieval-augmented chatbot that answers questions grounded in the user's own diary
  entries, with source citations back to the diary entries it drew from.
- Asynchronous background indexing pipeline: diary entries are chunked and embedded on create/edit
  without blocking the save flow, resumes automatically after a restart, and edits re-index the
  new content while removing stale versions.
- Deleting a diary entry removes its vectors from the store so the chatbot can no longer reference
  it.
- Per-user-scoped vector store (Qdrant) for diary embeddings, ensuring no cross-user retrieval
  leakage.
- Conversation persistence: start a new conversation, list past conversations by recent activity,
  reopen and continue one with prior turns as context, and delete a conversation with a
  confirmation step.
- Streaming chat responses with a visible in-progress indicator.
- Replies match the language of the question asked (Traditional Chinese or English).
- Scope-guarded responses: Genie answers only from retrieved diary content or Living Genie app
  help, and firmly declines unrelated requests.
- New `ollama`, `qdrant`, and `worker` services added to Docker Compose, so the full stack
  including local LLM inference still runs via `docker compose up`.

## [0.1.0] - 2026-07-25

### Added

- User registration and login with email/password, session-cookie auth.
- Diary entry create, list, view, edit, and delete, scoped to the authenticated user.
- Rich-text markdown editor (Tiptap) for diary content, including inline image upload and
  drag-and-drop.
- Multi-language UI (Traditional Chinese default, English), switchable at runtime.
- Containerized frontend, backend, and PostgreSQL database via Docker Compose, with data
  persisting across restarts.
