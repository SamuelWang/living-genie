import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/render';
import { DeleteConversationDialog } from './DeleteConversationDialog';
import { deleteConversation } from '@/api/conversations';

vi.mock('@/api/conversations');

const mockDeleteConversation = vi.mocked(deleteConversation);

describe('DeleteConversationDialog', () => {
  it('opens the confirmation dialog without calling delete', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <DeleteConversationDialog conversationId="1" conversationPreview="My conversation" />,
      { withAuthProvider: false },
    );

    await user.click(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(mockDeleteConversation).not.toHaveBeenCalled();
  });

  it('closes without deleting when cancel is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <DeleteConversationDialog conversationId="1" conversationPreview="My conversation" />,
      { withAuthProvider: false },
    );

    await user.click(screen.getByRole('button', { name: 'Delete' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(mockDeleteConversation).not.toHaveBeenCalled();
  });

  it('calls deleteConversation once and fires onDeleted when confirmed', async () => {
    const user = userEvent.setup();
    mockDeleteConversation.mockResolvedValue(undefined);
    const onDeleted = vi.fn();
    renderWithProviders(
      <DeleteConversationDialog
        conversationId="conv-1"
        conversationPreview="My conversation"
        onDeleted={onDeleted}
      />,
      { withAuthProvider: false },
    );

    await user.click(screen.getByRole('button', { name: 'Delete' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(onDeleted).toHaveBeenCalledTimes(1));
    expect(mockDeleteConversation).toHaveBeenCalledTimes(1);
    expect(mockDeleteConversation).toHaveBeenCalledWith('conv-1');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('keeps the dialog open and shows an alert when the delete request fails', async () => {
    const user = userEvent.setup();
    mockDeleteConversation.mockRejectedValue(new Error('failed'));
    renderWithProviders(
      <DeleteConversationDialog conversationId="1" conversationPreview="My conversation" />,
      { withAuthProvider: false },
    );

    await user.click(screen.getByRole('button', { name: 'Delete' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Something went wrong. Please try again.',
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
