import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import { renderWithProviders } from '@/test/render';
import { DiaryListPage } from './DiaryListPage';
import { listDiaryEntries } from '@/api/diaries';

vi.mock('@/api/diaries');

const mockListDiaryEntries = vi.mocked(listDiaryEntries);

describe('DiaryListPage', () => {
  it('renders entries in the exact order returned by the API', async () => {
    mockListDiaryEntries.mockResolvedValue([
      { id: '3', title: 'Third written, oldest date', entry_date: '2026-01-01' },
      { id: '1', title: 'First in API order', entry_date: '2026-03-15' },
      { id: '2', title: 'Second in API order', entry_date: '2026-02-10' },
    ]);

    renderWithProviders(<DiaryListPage />, { withAuthProvider: false });

    const list = await screen.findByRole('list');
    const titles = within(list)
      .getAllByRole('link')
      .map((link) => link.textContent);

    expect(titles).toEqual([
      expect.stringContaining('Third written, oldest date'),
      expect.stringContaining('First in API order'),
      expect.stringContaining('Second in API order'),
    ]);
  });

  it('shows an empty-state message when there are no entries', async () => {
    mockListDiaryEntries.mockResolvedValue([]);

    renderWithProviders(<DiaryListPage />, { withAuthProvider: false });

    expect(await screen.findByText('No diary entries yet.')).toBeInTheDocument();
  });

  it('shows a generic error message when the request fails', async () => {
    mockListDiaryEntries.mockRejectedValue(new Error('network error'));

    renderWithProviders(<DiaryListPage />, { withAuthProvider: false });

    await waitFor(() =>
      expect(screen.getByText('Something went wrong. Please try again.')).toBeInTheDocument(),
    );
  });
});
