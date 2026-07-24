import { randomUUID } from 'node:crypto';
import { expect, test } from '@playwright/test';

test('register → login → diary CRUD works → logout → protected routes redirect', async ({
  page,
}) => {
  const email = `e2e-auth-${randomUUID()}@example.com`;
  const password = 'correct-horse-1';

  await page.goto('/register');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Register' }).click();
  await page.waitForURL('**/login');

  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Log in' }).click();
  await page.waitForURL('**/diaries');

  await page.getByRole('button', { name: 'New entry' }).click();
  await page.getByLabel('Title').fill('Auth flow entry');
  await page.getByRole('button', { name: 'Create entry' }).click();
  await page.waitForURL('**/diaries');
  await expect(page.getByRole('link', { name: /Auth flow entry/ })).toBeVisible();

  await page.getByRole('button', { name: 'Log out' }).click();
  await page.waitForURL('**/login');

  await page.goto('/diaries');
  await page.waitForURL('**/login');
});
