import { randomUUID } from 'node:crypto';
import { expect, test } from '@playwright/test';
import { getLatestCodeForEmail, registerAndLogin } from './helpers.ts';

test('register → verify email → login → diary CRUD works → logout → protected routes redirect', async ({
  page,
}) => {
  const email = `e2e-auth-${randomUUID()}@example.com`;
  const password = 'correct-horse-1';

  await page.goto('/register');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Register' }).click();
  await page.waitForURL('**/verify-email**');

  const code = await getLatestCodeForEmail(email, { subjectContains: 'Verify' });
  await page.getByLabel('Verification code').fill(code);
  await page.getByRole('button', { name: 'Verify' }).click();
  await page.waitForURL('**/diaries'); // verify-email's auto-login

  await page.getByRole('button', { name: 'Log out' }).click();
  await page.waitForURL('**/login');

  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Log in' }).click();
  await page.waitForURL('**/diaries'); // plain login works post-verification

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

test('forgot password → reset password invalidates other sessions', async ({ page, browser }) => {
  const email = `e2e-reset-${randomUUID()}@example.com`;
  const oldPassword = 'correct-horse-1';
  const newPassword = 'new-correct-horse-2';

  await registerAndLogin(page, email, oldPassword); // session A, lands on /diaries

  const contextB = await browser.newContext();
  const pageB = await contextB.newPage();
  await pageB.goto('/login');
  await pageB.getByLabel('Email').fill(email);
  await pageB.getByLabel('Password').fill(oldPassword);
  await pageB.getByRole('button', { name: 'Log in' }).click();
  await pageB.waitForURL('**/diaries'); // session B, independent cookie jar

  await page.goto('/forgot-password');
  await page.getByLabel('Email').fill(email);
  await page.getByRole('button', { name: 'Send reset code' }).click();
  await expect(
    page.getByText("If that email is registered, we've sent a code to reset your password."),
  ).toBeVisible();

  const resetCode = await getLatestCodeForEmail(email, { subjectContains: 'Reset' });
  await page.goto(`/reset-password?email=${encodeURIComponent(email)}`);
  await page.getByLabel('Reset code').fill(resetCode);
  await page.getByLabel('New password').fill(newPassword);
  await page.getByRole('button', { name: 'Reset password' }).click();
  await page.waitForURL('**/login'); // reset-password does not auto-login

  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(oldPassword);
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page.getByText('Incorrect email or password')).toBeVisible();

  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(newPassword);
  await page.getByRole('button', { name: 'Log in' }).click();
  await page.waitForURL('**/diaries');

  await pageB.goto('/diaries');
  await pageB.waitForURL('**/login'); // session B was signed out server-side by the reset

  await contextB.close();
});
