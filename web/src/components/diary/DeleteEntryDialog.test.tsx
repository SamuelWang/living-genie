import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/render';
import { DeleteEntryDialog } from './DeleteEntryDialog';
import { deleteDiaryEntry } from '@/api/diaries';

vi.mock('@/api/diaries');

const mockDeleteDiaryEntry = vi.mocked(deleteDiaryEntry);

describe('DeleteEntryDialog', () => {
  it('opens the confirmation dialog without calling delete', async () => {
    const user = userEvent.setup();
    renderWithProviders(<DeleteEntryDialog entryId="1" entryTitle="My entry" />, {
      withAuthProvider: false,
    });

    await user.click(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(mockDeleteDiaryEntry).not.toHaveBeenCalled();
  });

  it('closes without deleting when cancel is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<DeleteEntryDialog entryId="1" entryTitle="My entry" />, {
      withAuthProvider: false,
    });

    await user.click(screen.getByRole('button', { name: 'Delete' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(mockDeleteDiaryEntry).not.toHaveBeenCalled();
  });

  it('calls deleteDiaryEntry once and fires onDeleted when confirmed', async () => {
    const user = userEvent.setup();
    mockDeleteDiaryEntry.mockResolvedValue(undefined);
    const onDeleted = vi.fn();
    renderWithProviders(
      <DeleteEntryDialog entryId="entry-1" entryTitle="My entry" onDeleted={onDeleted} />,
      { withAuthProvider: false },
    );

    await user.click(screen.getByRole('button', { name: 'Delete' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(onDeleted).toHaveBeenCalledTimes(1));
    expect(mockDeleteDiaryEntry).toHaveBeenCalledTimes(1);
    expect(mockDeleteDiaryEntry).toHaveBeenCalledWith('entry-1');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('keeps the dialog open and shows an alert when the delete request fails', async () => {
    const user = userEvent.setup();
    mockDeleteDiaryEntry.mockRejectedValue(new Error('failed'));
    renderWithProviders(<DeleteEntryDialog entryId="1" entryTitle="My entry" />, {
      withAuthProvider: false,
    });

    await user.click(screen.getByRole('button', { name: 'Delete' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Something went wrong. Please try again.',
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
