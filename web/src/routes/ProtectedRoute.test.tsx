import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { Route, Routes } from 'react-router';
import { renderWithProviders } from '@/test/render';
import { ProtectedRoute } from './ProtectedRoute';
import { getMe } from '@/api/auth';

vi.mock('@/api/auth');

const mockGetMe = vi.mocked(getMe);

function renderProtected(route = '/diaries') {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<div>Login page</div>} />
      <Route element={<ProtectedRoute />}>
        <Route path="/diaries" element={<div>Diaries page</div>} />
      </Route>
    </Routes>,
    { route },
  );
}

describe('ProtectedRoute', () => {
  it('shows a loading indicator before auth resolves', () => {
    mockGetMe.mockReturnValue(new Promise(() => {}));

    renderProtected();

    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('redirects unauthenticated users to /login', async () => {
    mockGetMe.mockResolvedValue(null);

    renderProtected();

    expect(await screen.findByText('Login page')).toBeInTheDocument();
  });

  it('renders the protected child for authenticated users', async () => {
    mockGetMe.mockResolvedValue({ id: '1', email: 'user@example.com', created_at: '2026-01-01' });

    renderProtected();

    expect(await screen.findByText('Diaries page')).toBeInTheDocument();
  });
});
