import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers.ts';

const FIXTURE_IMAGE = path.join(import.meta.dirname, 'fixtures', 'test-image.png');

test('insert an image via the editor and see it render in the saved entry', async ({ page }) => {
  const email = `e2e-image-${randomUUID()}@example.com`;
  await registerAndLogin(page, email);

  await page.getByRole('button', { name: 'New entry' }).click();
  await page.getByLabel('Title').fill('Entry with image');

  await page.locator('input[type="file"]').setInputFiles(FIXTURE_IMAGE);

  const editorImage = page.locator('.ProseMirror img');
  await expect(editorImage).toBeVisible();
  await expect(editorImage).toHaveAttribute('src', /\/media\//);

  await page.getByRole('button', { name: 'Create entry' }).click();
  await page.waitForURL('**/diaries');

  await page.getByRole('link', { name: /Entry with image/ }).click();

  const detailImage = page.locator('.ProseMirror img');
  await expect(detailImage).toBeVisible();
  await expect(detailImage).toHaveAttribute('src', /\/media\//);
});
