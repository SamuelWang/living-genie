# Living Genie Web

Frontend for [Living Genie](../README.md), a personal diary app. React + TypeScript + Vite,
providing registration/login, diary entry CRUD, and a rich-text editor with image uploads against
the `web-api` backend. See [../docs/architecture.md](../docs/architecture.md) and
[../docs/requirements/v0.1.0.md](../docs/requirements/v0.1.0.md) for the full design and
acceptance criteria this app implements.

## Prerequisites

- Node.js 20+ and [pnpm](https://pnpm.io/)
- A running `web-api` backend (see [../web-api/README.md](../web-api/README.md)) for the app to
  talk to in dev
- For end-to-end tests only: [uv](https://docs.astral.sh/uv/) and Docker (to run PostgreSQL
  locally) — see [Running tests](#running-tests) below

## Running locally

```sh
pnpm install
cp .env.example .env   # adjust VITE_API_URL if web-api isn't on localhost:8000
pnpm dev
```

The app is served at `http://localhost:5173`, matching `web-api`'s default `FRONTEND_ORIGIN`.

### Running via Docker

From the repo root:

```sh
cp web/.env.example web/.env   # adjust VITE_API_URL if web-api isn't on localhost:8000
docker compose up --build web
```

`VITE_API_URL` is baked into the static bundle at build time (Vite inlines `import.meta.env.*`),
so changing it requires rebuilding the image, not just restarting the container.

The image applies OS security patches (`apk upgrade`) at build time, but that layer is cached like
any other — rebuild periodically with `docker compose build --no-cache --pull web` to actually
pick up new upstream patches rather than reusing a stale cached layer.

### Development via Docker Compose (hot reload)

`docker-compose.dev.yaml` overrides `web` to run the Vite dev server against the source
bind-mounted from the host, so edits take effect immediately without an image rebuild:

```sh
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build web
```

The app is served at `http://localhost:5173` with HMR. Dependencies (`node_modules`) are
installed at image-build time and cached in a named volume — if you change
`package.json`/`pnpm-lock.yaml`, re-run the command above with `--build` to pick up the change.

## Configuration

All settings are read from Vite env vars, with `.env.example` as the source of truth for local
defaults:

| Variable       | Default                 | Description                     |
| -------------- | ------------------------ | -------------------------------- |
| `VITE_API_URL` | `http://localhost:8000` | Base URL of the `web-api` backend |

## Running tests

### Unit / component tests (Vitest + React Testing Library)

```sh
pnpm test         # single run
pnpm test:watch   # watch mode
```

Component tests mock the `@/api/*` modules directly rather than the network layer, and stub the
tiptap-based `DiaryEditor` wherever it's only a descendant of the component under test (see
`src/test/setup.ts` and `src/test/render.tsx`).

### End-to-end tests (Playwright)

```sh
pnpm exec playwright install   # first time only, installs browser binaries
pnpm test:e2e
```

Unlike the unit tests, e2e specs run against a **real** `web-api` instance and a real PostgreSQL
database rather than mocked responses, to get genuine integration coverage of the flows in
`docs/execution/v0.1.0.md`'s Section 9 (auth, diary CRUD, image upload). `pnpm test:e2e`:

1. Runs `web-api/scripts/init_e2e_db.py` (via Playwright's `globalSetup`) to create/migrate a
   dedicated `living_genie_e2e` database on the same Postgres instance used for local dev — your
   dev database is never touched. Override the target with `E2E_DATABASE_URL`.
2. Builds the frontend and serves it with `vite preview` on port 4173.
3. Starts `web-api` (`uv run uvicorn`) on port 8000, pointed at the `living_genie_e2e` database.
4. Runs the specs under `e2e/` against that stack in a real Chromium browser.

Requires Postgres reachable at `localhost:5432` (`docker compose up -d postgres` from the repo
root) and `uv` installed.

## Project layout

```
web/
├── src/
│   ├── api/           # Typed fetch wrapper functions + TS types mirroring backend schemas
│   ├── components/    # Shared UI (shadcn/ui primitives, diary, editor, layout)
│   ├── context/       # Auth context/provider
│   ├── hooks/         # useAuth, useImageUpload
│   ├── i18n/          # i18next configuration
│   ├── lib/           # Small framework-agnostic helpers (dates, class names)
│   ├── locales/       # zh-Hant (default) and en translation resources
│   ├── pages/         # Route-level components
│   ├── routes/        # Router setup + protected-route wrapper
│   └── test/          # Vitest setup + renderWithProviders test helper
└── e2e/               # Playwright specs, fixtures, and global setup
```
