import path from 'node:path';
import { defineConfig, devices } from '@playwright/test';

const WEB_API_ROOT = path.resolve(import.meta.dirname, '../web-api');
const E2E_DATABASE_URL =
  process.env.E2E_DATABASE_URL ??
  'postgresql+psycopg://living_genie:living_genie@localhost:5432/living_genie_e2e';

// Dedicated, e2e-only ports (distinct from the normal dev ports 8000/5173 and the
// scratch-verification ports 8090/5183 — see CLAUDE.md) so `reuseExistingServer` below can
// never accidentally reuse a developer's already-running dev server and silently send e2e
// traffic into the real dev database.
const E2E_API_PORT = Number(process.env.E2E_API_PORT ?? 8100);
const E2E_WEB_PORT = Number(process.env.E2E_WEB_PORT ?? 4183);
const E2E_API_URL = `http://localhost:${E2E_API_PORT}`;
const E2E_WEB_URL = `http://localhost:${E2E_WEB_PORT}`;

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: {
    baseURL: E2E_WEB_URL,
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `pnpm build && pnpm preview --port ${E2E_WEB_PORT}`,
      cwd: import.meta.dirname,
      port: E2E_WEB_PORT,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        VITE_API_URL: E2E_API_URL,
      },
    },
    {
      command: `uv run uvicorn app.main:app --port ${E2E_API_PORT}`,
      cwd: WEB_API_ROOT,
      port: E2E_API_PORT,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        DATABASE_URL: E2E_DATABASE_URL,
        FRONTEND_ORIGIN: E2E_WEB_URL,
        UPLOADS_DIR: 'uploads-e2e',
      },
    },
  ],
});
