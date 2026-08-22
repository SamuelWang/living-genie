import type { Page } from '@playwright/test';

const MAILPIT_URL = process.env.E2E_MAILPIT_URL ?? 'http://localhost:8025';

interface MailpitSearchResult {
  messages: { ID: string }[];
}

interface MailpitMessage {
  Text: string;
}

/**
 * Polls Mailpit's REST API for the newest email sent to `toAddress` (optionally filtered by a
 * subject substring, to disambiguate the verification email from a later reset-password email
 * sent to the same address) and extracts the plaintext code, matching the alphabet/length in
 * web-api/app/security.py's `_CODE_ALPHABET` / `settings.email_code_length`.
 */
export async function getLatestCodeForEmail(
  toAddress: string,
  { subjectContains, timeoutMs = 15_000, intervalMs = 500 }: { subjectContains?: string; timeoutMs?: number; intervalMs?: number } = {},
): Promise<string> {
  const query = subjectContains
    ? `to:${toAddress} subject:"${subjectContains}"`
    : `to:${toAddress}`;
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const searchRes = await fetch(`${MAILPIT_URL}/api/v1/search?query=${encodeURIComponent(query)}`);
    if (searchRes.ok) {
      const body = (await searchRes.json()) as MailpitSearchResult;
      const latest = body.messages?.[0];
      if (latest) {
        const msgRes = await fetch(`${MAILPIT_URL}/api/v1/message/${latest.ID}`);
        if (msgRes.ok) {
          const msg = (await msgRes.json()) as MailpitMessage;
          const match = /\b[A-HJ-NP-Z2-9]{8}\b/.exec(msg.Text ?? '');
          if (match) return match[0];
        }
      }
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error(`Timed out waiting for an email code sent to ${toAddress}`);
}

export async function registerAndLogin(page: Page, email: string, password = 'correct-horse-1') {
  await page.goto('/register');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Register' }).click();
  await page.waitForURL('**/verify-email**');

  const code = await getLatestCodeForEmail(email, { subjectContains: 'Verify' });
  await page.getByLabel('Verification code').fill(code);
  await page.getByRole('button', { name: 'Verify' }).click();
  // Verify-email itself creates the session (auto-login) — there is no separate login step here.
  await page.waitForURL('**/diaries');
}

const QDRANT_URL = process.env.E2E_QDRANT_URL ?? 'http://localhost:6333';

/**
 * Polls Qdrant directly (rather than the chat endpoint, where an empty-retrieval answer is also
 * a valid 200 response) for the worker to have indexed a diary entry or todo.
 */
export async function waitForIndexing(
  sourceType: 'diary_entry' | 'todo',
  sourceId: string,
  { timeoutMs = 60_000, intervalMs = 1_000 } = {},
) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const res = await fetch(`${QDRANT_URL}/collections/entry_chunks/points/scroll`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filter: {
          must: [
            { key: 'source_type', match: { value: sourceType } },
            { key: 'source_id', match: { value: sourceId } },
          ],
        },
        limit: 1,
      }),
    });
    if (res.ok) {
      const body = (await res.json()) as { result?: { points?: unknown[] } };
      if ((body.result?.points?.length ?? 0) > 0) return;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error(`Timed out waiting for ${sourceType} ${sourceId} to be indexed in Qdrant`);
}
