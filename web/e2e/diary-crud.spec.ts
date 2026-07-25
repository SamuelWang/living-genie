import { randomUUID } from 'node:crypto';
import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers.ts';

test('full CRUD flow through the UI: create → list → view → edit → delete', async ({ page }) => {
  const email = `e2e-crud-${randomUUID()}@example.com`;
  await registerAndLogin(page, email);

  await page.getByRole('button', { name: 'New entry' }).click();
  await page.getByLabel('Title').fill('My e2e entry');
  await page.getByRole('button', { name: 'Create entry' }).click();

  await page.waitForURL('**/diaries');
  await expect(page.getByRole('link', { name: /My e2e entry/ })).toBeVisible();

  await page.getByRole('link', { name: /My e2e entry/ }).click();
  await expect(page.getByRole('heading', { name: 'My e2e entry' })).toBeVisible();

  await page.getByRole('button', { name: 'Edit' }).click();
  await page.getByLabel('Title').fill('My e2e entry (edited)');
  await page.locator('.ProseMirror').click();
  await page.keyboard.type('Updated diary body text.');
  await page.getByRole('button', { name: 'Save changes' }).click();

  await expect(page.getByRole('heading', { name: 'My e2e entry (edited)' })).toBeVisible();
  await expect(
    page.locator('.ProseMirror', { hasText: 'Updated diary body text.' }),
  ).toBeVisible();

  await page.getByRole('button', { name: 'Delete' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click();

  await page.waitForURL('**/diaries');
  await expect(page.getByRole('link', { name: /My e2e entry \(edited\)/ })).toHaveCount(0);
});
