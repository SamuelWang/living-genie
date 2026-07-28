import type { Page } from '@playwright/test';

export async function registerAndLogin(page: Page, email: string, password = 'correct-horse-1') {
  await page.goto('/register');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Register' }).click();
  await page.waitForURL('**/login');

  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Log in' }).click();
  await page.waitForURL('**/diaries');
}

const QDRANT_URL = process.env.E2E_QDRANT_URL ?? 'http://localhost:6333';

/**
 * Polls Qdrant directly (rather than the chat endpoint, where an empty-retrieval answer is also
 * a valid 200 response) for the worker to have indexed a diary entry.
 */
export async function waitForIndexing(
  diaryEntryId: string,
  { timeoutMs = 60_000, intervalMs = 1_000 } = {},
) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const res = await fetch(`${QDRANT_URL}/collections/diary_chunks/points/scroll`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filter: { must: [{ key: 'diary_entry_id', match: { value: diaryEntryId } }] },
        limit: 1,
      }),
    });
    if (res.ok) {
      const body = (await res.json()) as { result?: { points?: unknown[] } };
      if ((body.result?.points?.length ?? 0) > 0) return;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error(`Timed out waiting for diary entry ${diaryEntryId} to be indexed in Qdrant`);
}
