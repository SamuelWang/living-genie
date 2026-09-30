# Living Genie

Living Genie is a personal living assistant web application that integrates local LLM models
(via Ollama) to help you work with your own personal data — a diary and todos, with more data
sources planned. Register an account, log in, and keep a private, dated diary with rich markdown
formatting and inline images, alongside a todo list. **Genie** is a chatbot that answers questions
grounded in your own diary entries and todos, with citations back to the sources it drew from, and
can create, update, complete, or delete todos for you through chat — powered entirely by local
models, with no external API calls.

## Stack

- **Frontend** ([web/](web/)) — React + TypeScript, Tiptap editor, Tailwind + shadcn/ui.
- **Backend** ([web-api/](web-api/)) — FastAPI + SQLAlchemy, PostgreSQL, cookie-session auth.
- **Database** — PostgreSQL, running as its own container.
- **AI / retrieval** — Ollama for local LLM inference (embedding + chat models) and Qdrant as
  the vector store for diary and todo embeddings, with a background worker handling asynchronous
  chunking and indexing.
- **Observability** — structured logs, Prometheus metrics, and OpenTelemetry traces from the
  backend and worker, collected by a self-hosted Prometheus, Loki, Tempo, and Grafana stack (with
  Grafana Alloy as the OTLP collector). No external accounts are needed and no telemetry leaves
  the host.

Each of these runs as its own Docker container, orchestrated locally via Docker Compose. See
[docs/architecture.md](docs/architecture.md) for the full technical design.

## Running the stack

Prerequisites: Docker and Docker Compose.

```sh
cp .env.example .env
cp web-api/.env.example web-api/.env
cp web/.env.example web/.env
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build
```

On first run, an `ollama-init` service automatically pulls the embedding and chat models, so the
initial `docker compose up` will take longer while they download. An NVIDIA GPU is used
automatically if available, but is not required — Ollama falls back to CPU inference.

Once healthy, the frontend is at `http://localhost:5173` and the backend API is at
`http://localhost:8000`. The `docker-compose.dev.yaml` overlay also starts a local Mailpit
instance, which catches account verification and password-reset emails instead of sending them
for real — view them at `http://localhost:8025`. In production, point the `SMTP_*` env vars in
`web-api/.env` at a real provider instead.

Grafana is at `http://localhost:3000` (log in with `GRAFANA_ADMIN_USER`/`GRAFANA_ADMIN_PASSWORD`
from `.env`, `admin`/`admin` by default), pre-provisioned with the Prometheus, Loki, and Tempo data
sources and a "Living Genie overview" dashboard. Prometheus is at `http://localhost:9090`.
Retention, the OTLP endpoint, and the trace sampling rate are set in `web-api/.env` (see
[web-api/README.md](web-api/README.md#configuration)).

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
