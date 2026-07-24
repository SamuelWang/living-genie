import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DiaryEntryForm } from './DiaryEntryForm';

vi.mock('@/components/editor/DiaryEditor', () => ({
  DiaryEditor: ({ content, onChange }: { content: string; onChange: (value: string) => void }) => (
    <textarea
      data-testid="mock-editor"
      value={content}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}));

describe('DiaryEntryForm', () => {
  it('blocks submit and shows alerts when title and date are missing', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <DiaryEntryForm
        initialValues={{ title: '', entry_date: '', content: '' }}
        submitLabel="diary.createSubmit"
        submitting={false}
        onSubmit={onSubmit}
      />,
    );

    await user.click(screen.getByRole('button', { name: /create entry/i }));

    expect(await screen.findByText('Title is required')).toBeInTheDocument();
    expect(screen.getByText('Date is required')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('does not show validation alerts before the first submit attempt', () => {
    render(
      <DiaryEntryForm
        initialValues={{ title: 'Existing entry', entry_date: '2026-01-01', content: '' }}
        submitLabel="diary.editSubmit"
        submitting={false}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.queryByText('Title is required')).not.toBeInTheDocument();
    expect(screen.queryByText('Date is required')).not.toBeInTheDocument();
  });

  it('submits trimmed values once title and date are valid', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <DiaryEntryForm
        initialValues={{ title: '', entry_date: '2026-01-01', content: '' }}
        submitLabel="diary.createSubmit"
        submitting={false}
        onSubmit={onSubmit}
      />,
    );

    await user.type(screen.getByLabelText('Title'), '  My entry  ');
    await user.click(screen.getByRole('button', { name: /create entry/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      title: 'My entry',
      entry_date: '2026-01-01',
      content: '',
    });
  });
});
