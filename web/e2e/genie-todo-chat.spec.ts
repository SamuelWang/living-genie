import { randomUUID } from 'node:crypto';
import { expect, test } from '@playwright/test';
import { registerAndLogin, waitForIndexing } from './helpers.ts';

const COMPOSER_PLACEHOLDER = 'Ask Genie about your diary or todos…';

async function createTodo(page: import('@playwright/test').Page, title: string, description?: string) {
  await page.goto('/todos');
  await page.getByRole('button', { name: 'New todo' }).click();
  await page.getByLabel('Title').fill(title);
  if (description) {
    await page.getByLabel('Description').fill(description);
  }
  await page.getByRole('button', { name: 'Create todo' }).click();
  await page.waitForURL('**/todos');
  await page.getByRole('link', { name: new RegExp(title) }).click();
  await page.waitForURL(/\/todos\/[^/]+$/);
  return page.url().split('/').pop()!;
}

async function askGenie(page: import('@playwright/test').Page, question: string) {
  await page.goto('/genie');
  await page.getByRole('button', { name: 'New chat' }).click();
  await page.getByPlaceholder(COMPOSER_PLACEHOLDER).fill(question);
  await page.getByRole('button', { name: 'Send' }).click();
  await page.waitForURL(/\/genie\/[^/]+$/);
}

async function sendAndWaitForReply(page: import('@playwright/test').Page, message: string) {
  const composer = page.getByPlaceholder(COMPOSER_PLACEHOLDER);
  await composer.fill(message);
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(composer).toBeDisabled();
  await expect(composer).not.toBeDisabled({ timeout: 60_000 });
}

test('ask Genie about a todo, get a grounded reply with a reference chip', async ({ page }) => {
  const email = `e2e-genie-todo-${randomUUID()}@example.com`;
  await registerAndLogin(page, email);

  const title = 'Buy groceries for the week';
  const todoId = await createTodo(
    page,
    title,
    'Need to pick up milk, eggs, and bread from the store before the weekend.',
  );

  await waitForIndexing('todo', todoId);

  await askGenie(page, 'What do I need to buy at the store?');

  await expect(page.locator(`a[href="/todos/${todoId}"]`)).toBeVisible({ timeout: 60_000 });
});

test('ask Genie to create a todo via chat with no confirmation required', async ({ page }) => {
  const email = `e2e-genie-todo-create-${randomUUID()}@example.com`;
  await registerAndLogin(page, email);

  const title = `Water the plants ${randomUUID().slice(0, 8)}`;
  await askGenie(page, `Please create a todo called "${title}".`);

  await expect(page.getByRole('link', { name: title })).toBeVisible({ timeout: 60_000 });

  await page.goto('/todos');
  await expect(page.getByRole('link', { name: new RegExp(title) })).toBeVisible();
});

test('ask Genie to complete a todo via chat, which requires confirmation first', async ({
  page,
}) => {
  const email = `e2e-genie-todo-complete-${randomUUID()}@example.com`;
  await registerAndLogin(page, email);

  const title = `Finish the report ${randomUUID().slice(0, 8)}`;
  await createTodo(page, title);

  await page.goto('/genie');
  await page.getByRole('button', { name: 'New chat' }).click();
  await sendAndWaitForReply(page, `Please mark "${title}" as complete.`);
  const conversationUrl = page.url();

  await page.goto('/todos');
  const rowBeforeConfirm = page.getByRole('link', { name: new RegExp(title) }).locator('xpath=..');
  await expect(rowBeforeConfirm.getByRole('checkbox', { name: 'Completed' })).not.toBeChecked();

  await page.goto(conversationUrl);
  await sendAndWaitForReply(page, 'Yes, please go ahead.');

  await page.goto('/todos');
  const rowAfterConfirm = page.getByRole('link', { name: new RegExp(title) }).locator('xpath=..');
  await expect(rowAfterConfirm.getByRole('checkbox', { name: 'Completed' })).toBeChecked();
});
