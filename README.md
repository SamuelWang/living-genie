# Living Genie

Living Genie is a personal living assistant web application that integrates local LLM models
(via Ollama) to help you work with your own personal data — starting with a diary. Register an
account, log in, and keep a private, dated diary with rich markdown formatting and inline
images. **Genie** is a chatbot that answers questions grounded in your own diary entries, with
citations back to the entries it drew from — powered entirely by local models, with no external
API calls.

## Stack

- **Frontend** ([web/](web/)) — React + TypeScript, Tiptap editor, Tailwind + shadcn/ui.
- **Backend** ([web-api/](web-api/)) — FastAPI + SQLAlchemy, PostgreSQL, cookie-session auth.
- **Database** — PostgreSQL, running as its own container.
- **AI / retrieval** — Ollama for local LLM inference (embedding + chat models) and Qdrant as
  the vector store for diary embeddings, with a background worker handling asynchronous
  chunking and indexing.

Each of these runs as its own Docker container, orchestrated locally via Docker Compose. See
[docs/architecture.md](docs/architecture.md) for the full technical design.

## Running the stack

Prerequisites: Docker and Docker Compose.

```sh
cp .env.example .env
cp web-api/.env.example web-api/.env
cp web/.env.example web/.env
docker compose up --build
```

On first run, an `ollama-init` service automatically pulls the embedding and chat models, so the
initial `docker compose up` will take longer while they download. An NVIDIA GPU is used
automatically if available, but is not required — Ollama falls back to CPU inference.

Once healthy, the frontend is at `http://localhost:5173` and the backend API is at
`http://localhost:8000`.

For local (non-Docker) development, running tests, and full configuration reference, see
[web/README.md](web/README.md) and [web-api/README.md](web-api/README.md).

## Documentation

- [docs/architecture.md](docs/architecture.md) — technical design.
- [docs/ollama-model-evaluation.md](docs/ollama-model-evaluation.md) — how to test a candidate
  Ollama model on your hardware before configuring it.
- [docs/requirements/](docs/requirements/) — functional requirements and acceptance criteria per
  release.
- [docs/roadmap.md](docs/roadmap.md) — what's planned next.
- [docs/release-notes/](docs/release-notes/) — user-facing summaries per release.
- [CHANGELOG.md](CHANGELOG.md) — notable changes by version.

## License

AGPL-3.0 — see [LICENSE](LICENSE).
