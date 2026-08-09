import { randomUUID } from 'node:crypto';
import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers.ts';

test('full CRUD flow through the UI: create → list → view → toggle → edit → delete', async ({
  page,
}) => {
  const email = `e2e-todo-crud-${randomUUID()}@example.com`;
  await registerAndLogin(page, email);

  await page.goto('/todos');
  await page.getByRole('button', { name: 'New todo' }).click();
  await page.getByLabel('Title').fill('My e2e todo');
  await page.getByRole('button', { name: 'Create todo' }).click();

  await page.waitForURL('**/todos');
  await expect(page.getByRole('link', { name: /My e2e todo/ })).toBeVisible();

  await page.getByRole('link', { name: /My e2e todo/ }).click();
  await expect(page.getByRole('heading', { name: 'My e2e todo' })).toBeVisible();

  await page.getByRole('checkbox', { name: 'Completed' }).click();
  await expect(page.getByRole('checkbox', { name: 'Completed' })).toBeChecked();

  await page.getByRole('button', { name: 'Edit' }).click();
  await page.getByLabel('Title').fill('My e2e todo (edited)');
  await page.getByRole('button', { name: 'Save changes' }).click();

  await expect(page.getByRole('heading', { name: 'My e2e todo (edited)' })).toBeVisible();

  await page.getByRole('button', { name: 'Delete' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click();

  await page.waitForURL('**/todos');
  await expect(page.getByRole('link', { name: /My e2e todo \(edited\)/ })).toHaveCount(0);
});
