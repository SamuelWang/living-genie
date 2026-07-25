# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-07-25

### Added

- User registration and login with email/password, session-cookie auth.
- Diary entry create, list, view, edit, and delete, scoped to the authenticated user.
- Rich-text markdown editor (Tiptap) for diary content, including inline image upload and
  drag-and-drop.
- Multi-language UI (Traditional Chinese default, English), switchable at runtime.
- Containerized frontend, backend, and PostgreSQL database via Docker Compose, with data
  persisting across restarts.
