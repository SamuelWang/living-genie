import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import { renderWithProviders } from '@/test/render';
import { LoginPage } from './LoginPage';
import { getMe, login } from '@/api/auth';
import { ApiError } from '@/api/errors';

vi.mock('@/api/auth');

const mockGetMe = vi.mocked(getMe);
const mockLogin = vi.mocked(login);

function renderLoginPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/diaries" element={<div>Diaries page</div>} />
    </Routes>,
    { route: '/login' },
  );
}

describe('LoginPage', () => {
  beforeEach(() => {
    mockGetMe.mockResolvedValue(null);
  });

  it('shows alerts for empty fields and does not attempt to log in', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    await user.click(screen.getByRole('button', { name: 'Log in' }));

    expect(await screen.findByText('Email is required')).toBeInTheDocument();
    expect(screen.getByText('Password is required')).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('shows a generic invalid-credentials message on 401', async () => {
    const user = userEvent.setup();
    mockLogin.mockRejectedValue(new ApiError(401, 'Incorrect email or password'));
    renderLoginPage();

    await user.type(screen.getByLabelText('Email'), 'user@example.com');
    await user.type(screen.getByLabelText('Password'), 'wrong-password');
    await user.click(screen.getByRole('button', { name: 'Log in' }));

    expect(await screen.findByText('Incorrect email or password')).toBeInTheDocument();
  });

  it('shows a generic error message on other failures', async () => {
    const user = userEvent.setup();
    mockLogin.mockRejectedValue(new ApiError(500, 'boom'));
    renderLoginPage();

    await user.type(screen.getByLabelText('Email'), 'user@example.com');
    await user.type(screen.getByLabelText('Password'), 'some-password');
    await user.click(screen.getByRole('button', { name: 'Log in' }));

    expect(await screen.findByText('Something went wrong. Please try again.')).toBeInTheDocument();
  });

  it('navigates to the diary list on successful login', async () => {
    const user = userEvent.setup();
    mockLogin.mockResolvedValue({ id: '1', email: 'user@example.com', created_at: '2026-01-01' });
    renderLoginPage();

    await user.type(screen.getByLabelText('Email'), 'user@example.com');
    await user.type(screen.getByLabelText('Password'), 'correct-password');
    await user.click(screen.getByRole('button', { name: 'Log in' }));

    await waitFor(() => expect(screen.getByText('Diaries page')).toBeInTheDocument());
  });
});
