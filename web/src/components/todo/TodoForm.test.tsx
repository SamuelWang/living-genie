import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TodoForm } from './TodoForm';

describe('TodoForm', () => {
  it('blocks submit and shows an alert when title is missing', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <TodoForm
        initialValues={{ title: '', description: '', due_date: null }}
        submitLabel="todo.createSubmit"
        submitting={false}
        onSubmit={onSubmit}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Create todo' }));

    expect(await screen.findByText('Title is required')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('does not show a validation alert before the first submit attempt', () => {
    render(
      <TodoForm
        initialValues={{ title: 'Existing todo', description: '', due_date: null }}
        submitLabel="todo.editSubmit"
        submitting={false}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.queryByText('Title is required')).not.toBeInTheDocument();
  });

  it('submits trimmed title, description, and due_date once title is valid', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <TodoForm
        initialValues={{ title: '', description: '', due_date: null }}
        submitLabel="todo.createSubmit"
        submitting={false}
        onSubmit={onSubmit}
      />,
    );

    await user.type(screen.getByLabelText('Title'), '  My todo  ');
    await user.type(screen.getByLabelText('Description'), 'Some details');
    await user.type(screen.getByLabelText('Due date'), '2026-01-15');
    await user.click(screen.getByRole('button', { name: 'Create todo' }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      title: 'My todo',
      description: 'Some details',
      due_date: '2026-01-15',
    });
  });

  it('submits a null due_date when the due date field is left empty', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <TodoForm
        initialValues={{ title: '', description: '', due_date: null }}
        submitLabel="todo.createSubmit"
        submitting={false}
        onSubmit={onSubmit}
      />,
    );

    await user.type(screen.getByLabelText('Title'), 'My todo');
    await user.click(screen.getByRole('button', { name: 'Create todo' }));

    expect(onSubmit).toHaveBeenCalledWith({
      title: 'My todo',
      description: '',
      due_date: null,
    });
  });
});
