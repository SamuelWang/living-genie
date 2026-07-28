import { randomUUID } from 'node:crypto';
import { expect, test } from '@playwright/test';
import { registerAndLogin, waitForIndexing } from './helpers.ts';

test('ask Genie about a diary entry, get a grounded reply with a citation, then delete the chat', async ({
  page,
}) => {
  const email = `e2e-genie-${randomUUID()}@example.com`;
  await registerAndLogin(page, email);

  const title = 'Genie e2e hiking trip';
  await page.getByRole('button', { name: 'New entry' }).click();
  await page.getByLabel('Title').fill(title);
  await page.locator('.ProseMirror').click();
  await page.keyboard.type(
    'On our trip to Yosemite Valley last week, we hiked to the top of Half Dome and watched the sunset over the granite cliffs.',
  );
  await page.getByRole('button', { name: 'Create entry' }).click();
  await page.waitForURL('**/diaries');

  await page.getByRole('link', { name: new RegExp(title) }).click();
  await page.waitForURL(/\/diaries\/[^/]+$/);
  const diaryEntryId = page.url().split('/').pop()!;

  await waitForIndexing(diaryEntryId);

  await page.goto('/genie');
  await page.getByRole('button', { name: 'New chat' }).click();

  const question = 'Where did I go hiking recently, and what did I see there?';
  await page.getByPlaceholder('Ask Genie about your diary…').fill(question);
  await page.getByRole('button', { name: 'Send' }).click();

  await page.waitForURL(/\/genie\/[^/]+$/);
  await expect(page.locator(`a[href="/diaries/${diaryEntryId}"]`)).toBeVisible({
    timeout: 60_000,
  });

  await page.goto('/genie');
  await expect(page.getByText(question)).toBeVisible();
  await page.getByRole('button', { name: 'Delete' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click();

  await expect(page.getByText(question)).toHaveCount(0);
});
