# Living Genie

Living Genie is a personal living assistant web application that will eventually integrate
local LLM models (via Ollama) to help you work with your own personal data — starting with a
diary. **v0.1.0** stands up the core app: register an account, log in, and keep a private,
dated diary with rich markdown formatting and inline images. No AI/LLM functionality is part of
this release yet.

## Stack

- **Frontend** ([web/](web/)) — React + TypeScript, Tiptap editor, Tailwind + shadcn/ui.
- **Backend** ([web-api/](web-api/)) — FastAPI + SQLAlchemy, PostgreSQL, cookie-session auth.
- **Database** — PostgreSQL, running as its own container.

All three run as separate Docker containers, orchestrated locally via Docker Compose. See
[docs/architecture.md](docs/architecture.md) for the full technical design.

## Running the stack

Prerequisites: Docker and Docker Compose.

```sh
cp .env.example .env
cp web-api/.env.example web-api/.env
cp web/.env.example web/.env
docker compose up --build
```

Once healthy, the frontend is at `http://localhost:5173` and the backend API is at
`http://localhost:8000`.

For local (non-Docker) development, running tests, and full configuration reference, see
[web/README.md](web/README.md) and [web-api/README.md](web-api/README.md).

## Documentation

- [docs/architecture.md](docs/architecture.md) — technical design.
- [docs/requirements/v0.1.0.md](docs/requirements/v0.1.0.md) — functional requirements and
  acceptance criteria for this release.
- [docs/roadmap.md](docs/roadmap.md) — what's planned beyond v0.1.0.
- [docs/release-notes/v0.1.0.md](docs/release-notes/v0.1.0.md) — user-facing summary of this
  release.
- [CHANGELOG.md](CHANGELOG.md) — notable changes by version.

## License

AGPL-3.0 — see [LICENSE](LICENSE).
