import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/render';
import { TodoListPage } from './TodoListPage';
import { listTodos, updateTodo } from '@/api/todos';
import { formatEntryDate } from '@/lib/date';
import type { TodoSummary } from '@/api/types';

vi.mock('@/api/todos');

const mockListTodos = vi.mocked(listTodos);
const mockUpdateTodo = vi.mocked(updateTodo);

function todo(overrides: Partial<TodoSummary> = {}): TodoSummary {
  return {
    id: '1',
    title: 'A todo',
    due_date: null,
    completed: false,
    ...overrides,
  };
}

describe('TodoListPage', () => {
  it('renders todos in the exact order returned by the API', async () => {
    mockListTodos.mockResolvedValue([
      todo({ id: '3', title: 'Third written' }),
      todo({ id: '1', title: 'First in API order' }),
      todo({ id: '2', title: 'Second in API order' }),
    ]);

    renderWithProviders(<TodoListPage />, { withAuthProvider: false });

    const list = await screen.findByRole('list');
    const titles = within(list)
      .getAllByRole('link')
      .map((link) => link.textContent);

    expect(titles).toEqual([
      expect.stringContaining('Third written'),
      expect.stringContaining('First in API order'),
      expect.stringContaining('Second in API order'),
    ]);
    expect(mockListTodos).toHaveBeenCalledWith(undefined);
  });

  it('shows an empty-state message when there are no todos', async () => {
    mockListTodos.mockResolvedValue([]);

    renderWithProviders(<TodoListPage />, { withAuthProvider: false });

    expect(await screen.findByText('No todos yet.')).toBeInTheDocument();
  });

  it('shows a generic error message when the request fails', async () => {
    mockListTodos.mockRejectedValue(new Error('network error'));

    renderWithProviders(<TodoListPage />, { withAuthProvider: false });

    await waitFor(() =>
      expect(screen.getByText('Something went wrong. Please try again.')).toBeInTheDocument(),
    );
  });

  it('filters by completion status and shows a filtered empty state', async () => {
    const user = userEvent.setup();
    mockListTodos.mockImplementation((completed) =>
      Promise.resolve(completed === false ? [] : [todo({ title: 'Some todo' })]),
    );

    renderWithProviders(<TodoListPage />, { withAuthProvider: false });

    expect(await screen.findByText('Some todo')).toBeInTheDocument();

    const pendingButton = screen.getByRole('button', { name: 'Pending' });
    await user.click(pendingButton);

    await waitFor(() => expect(mockListTodos).toHaveBeenCalledWith(false));
    expect(pendingButton).toHaveAttribute('aria-pressed', 'true');
    expect(await screen.findByText('No todos match this filter.')).toBeInTheDocument();
  });

  it('toggles completion via the checkbox', async () => {
    const user = userEvent.setup();
    mockListTodos.mockResolvedValue([todo({ id: 'todo-1', title: 'Toggle me', completed: false })]);
    mockUpdateTodo.mockResolvedValue({
      id: 'todo-1',
      title: 'Toggle me',
      description: null,
      due_date: null,
      completed: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });

    renderWithProviders(<TodoListPage />, { withAuthProvider: false });

    const checkbox = await screen.findByRole('checkbox', { name: 'Completed' });
    await user.click(checkbox);

    await waitFor(() =>
      expect(mockUpdateTodo).toHaveBeenCalledWith('todo-1', { completed: true }),
    );
  });

  it('renders a due date when present and omits it when absent', async () => {
    mockListTodos.mockResolvedValue([
      todo({ id: '1', title: 'Has a due date', due_date: '2026-01-15' }),
      todo({ id: '2', title: 'No due date', due_date: null }),
    ]);

    renderWithProviders(<TodoListPage />, { withAuthProvider: false });

    expect(await screen.findByText(formatEntryDate('2026-01-15', 'en'))).toBeInTheDocument();
  });
});
