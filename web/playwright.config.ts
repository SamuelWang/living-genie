import path from 'node:path';
import { defineConfig, devices } from '@playwright/test';

const WEB_API_ROOT = path.resolve(import.meta.dirname, '../web-api');
const E2E_DATABASE_URL =
  process.env.E2E_DATABASE_URL ??
  'postgresql+psycopg://living_genie:living_genie@localhost:5432/living_genie_e2e';

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'pnpm build && pnpm preview --port 4173',
      cwd: import.meta.dirname,
      port: 4173,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: 'uv run uvicorn app.main:app --port 8000',
      cwd: WEB_API_ROOT,
      port: 8000,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        DATABASE_URL: E2E_DATABASE_URL,
        FRONTEND_ORIGIN: 'http://localhost:4173',
        UPLOADS_DIR: 'uploads-e2e',
      },
    },
  ],
});
