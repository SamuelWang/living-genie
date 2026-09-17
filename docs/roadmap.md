# Roadmap

## v0.1.0

- Initialize the frontend and backend infrastructure, containerized and runnable locally.
- Implement user registration and login with email and password.
- Implement full diary CRUD (create, view, edit, delete), scoped to the authenticated user.
- Support a multi-language UI, defaulting to Traditional Chinese and switchable to English.

## v0.2.0

- Initialize the infrastructure for the asynchronous RAG/chunking workflow.
- Add a vector database for storing embedding vectors.
- Implement the RAG workflow over diary entries.
- Implement a single chatbot feature for diaries and future data sources.

## v0.3.0

- Compress uploaded images to the smallest possible size using lossless compression.
- Implement full todo CRUD (create, view, edit, delete), scoped to the authenticated user.
- Extend Genie with tool-calling so it can answer questions about the user's todos and create,
  update, complete, or delete them through chat.

## v0.4.0

- Require new accounts to verify their email address before they can log in.
- Let users reset a forgotten password via an emailed link.
- Store the user's language preference on their account so verification/reset emails (and
  future account-wide content) can be sent in it.

## v0.5.0

- Add structured logging across the backend and worker, replacing ad-hoc console logging.
- Add a self-hosted observability stack (Prometheus, Loki, Tempo, Grafana) for metrics, log
  aggregation, and distributed tracing.
- Instrument the backend and worker with request/job metrics and distributed traces across the
  API, worker, Postgres, Qdrant, and Ollama calls, including stage-level spans for the chat/RAG
  pipeline and the indexing worker's chunk/embed/upsert pipeline.
- Provide Grafana dashboards correlating logs, metrics, and traces for debugging.
