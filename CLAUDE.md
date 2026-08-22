# Living Genie

Personal diary/todo app. Backend in `web-api/` (FastAPI + Postgres + Qdrant), frontend in `web/`
(React + Vite). See each directory's README for setup.

## Manual/ad-hoc verification

The `living_genie` Postgres database is the developer's real dev data (this is a personal diary
app — it may hold real diary entries, todos, etc.), not disposable test fixtures. Automated tests
already avoid it (pytest uses `living_genie_test`, Playwright e2e uses `living_genie_e2e`, both
documented in `web-api/README.md`).

When doing throwaway manual verification during implementation — registering a user to check a UI
state, a one-off curl request, clicking through a flow to confirm something renders correctly —
run against the scratch stack instead of whatever dev server the user may already have running:

```sh
# backend (web-api/)
uv run python scripts/init_scratch_db.py   # once, or to reset to a clean slate
DATABASE_URL=postgresql+psycopg://living_genie:living_genie@localhost:5432/living_genie_scratch \
  FRONTEND_ORIGIN=http://localhost:5183 \
  uv run uvicorn app.main:app --reload --port 8090

# frontend (web/)
VITE_API_URL=http://localhost:8090 pnpm dev --port 5183
```

Never register throwaway/test users or write ad-hoc verification data against port 8000/5173 (the
normal dev ports) or the `living_genie` database directly.
