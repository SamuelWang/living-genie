import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import { renderWithProviders } from '@/test/render';
import { GenieListPage } from './GenieListPage';
import { listConversations } from '@/api/conversations';

vi.mock('@/api/conversations');

const mockListConversations = vi.mocked(listConversations);

describe('GenieListPage', () => {
  it('renders conversations in the exact order returned by the API', async () => {
    mockListConversations.mockResolvedValue([
      {
        id: '3',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-03T00:00:00Z',
        preview: 'Third written, most recently updated',
      },
      {
        id: '1',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        preview: 'First in API order',
      },
      {
        id: '2',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
        preview: 'Second in API order',
      },
    ]);

    renderWithProviders(<GenieListPage />, { withAuthProvider: false });

    const list = await screen.findByRole('list');
    const titles = within(list)
      .getAllByRole('link')
      .map((link) => link.textContent);

    expect(titles).toEqual([
      expect.stringContaining('Third written, most recently updated'),
      expect.stringContaining('First in API order'),
      expect.stringContaining('Second in API order'),
    ]);
  });

  it('shows a fallback label for conversations with no preview', async () => {
    mockListConversations.mockResolvedValue([
      { id: '1', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z', preview: null },
    ]);

    renderWithProviders(<GenieListPage />, { withAuthProvider: false });

    expect(await screen.findByText('New conversation')).toBeInTheDocument();
  });

  it('shows an empty-state message when there are no conversations', async () => {
    mockListConversations.mockResolvedValue([]);

    renderWithProviders(<GenieListPage />, { withAuthProvider: false });

    expect(await screen.findByText('No conversations yet.')).toBeInTheDocument();
  });

  it('shows a generic error message when the request fails', async () => {
    mockListConversations.mockRejectedValue(new Error('network error'));

    renderWithProviders(<GenieListPage />, { withAuthProvider: false });

    await waitFor(() =>
      expect(screen.getByText('Something went wrong. Please try again.')).toBeInTheDocument(),
    );
  });
});
