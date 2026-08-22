import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import { renderWithProviders } from '@/test/render';
import { ResetPasswordPage } from './ResetPasswordPage';
import { getMe, resetPassword } from '@/api/auth';
import { ApiError } from '@/api/errors';

vi.mock('@/api/auth');

const mockGetMe = vi.mocked(getMe);
const mockResetPassword = vi.mocked(resetPassword);

function renderResetPasswordPage(route = '/reset-password') {
  return renderWithProviders(
    <Routes>
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/login" element={<div>Login page</div>} />
    </Routes>,
    { route },
  );
}

const fullUser = {
  id: '1',
  email: 'user@example.com',
  locale: 'en',
  created_at: '2026-01-01',
  email_verified: true,
};

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    mockGetMe.mockResolvedValue(null);
  });

  it('pre-fills and locks the email field when provided via query param', () => {
    renderResetPasswordPage('/reset-password?email=user%40example.com');

    const emailInput = screen.getByLabelText('Email');
    expect(emailInput).toHaveValue('user@example.com');
    expect(emailInput).toHaveAttribute('readonly');
  });

  it('shows required-field alerts on empty submit', async () => {
    const user = userEvent.setup();
    renderResetPasswordPage();

    await user.click(screen.getByRole('button', { name: 'Reset password' }));

    expect(await screen.findByText('Email is required')).toBeInTheDocument();
    expect(screen.getByText('Reset code is required')).toBeInTheDocument();
    expect(screen.getByText('Password is required')).toBeInTheDocument();
    expect(mockResetPassword).not.toHaveBeenCalled();
  });

  it('shows a too-short-password alert', async () => {
    const user = userEvent.setup();
    renderResetPasswordPage();

    await user.type(screen.getByLabelText('Email'), 'user@example.com');
    await user.type(screen.getByLabelText('Reset code'), 'ABCD1234');
    await user.type(screen.getByLabelText('New password'), 'short12');
    await user.click(screen.getByRole('button', { name: 'Reset password' }));

    expect(await screen.findByText('Password must be at least 8 characters')).toBeInTheDocument();
    expect(mockResetPassword).not.toHaveBeenCalled();
  });

  it('navigates to /login on success', async () => {
    const user = userEvent.setup();
    mockResetPassword.mockResolvedValue(fullUser);
    renderResetPasswordPage('/reset-password?email=user%40example.com');

    await user.type(screen.getByLabelText('Reset code'), 'ABCD1234');
    await user.type(screen.getByLabelText('New password'), 'longenoughpassword');
    await user.click(screen.getByRole('button', { name: 'Reset password' }));

    await waitFor(() => expect(screen.getByText('Login page')).toBeInTheDocument());
  });

  it('shows a generic invalid-or-expired-code message on error', async () => {
    const user = userEvent.setup();
    mockResetPassword.mockRejectedValue(new ApiError(400, 'Invalid or expired code'));
    renderResetPasswordPage('/reset-password?email=user%40example.com');

    await user.type(screen.getByLabelText('Reset code'), 'WRONGCOD');
    await user.type(screen.getByLabelText('New password'), 'longenoughpassword');
    await user.click(screen.getByRole('button', { name: 'Reset password' }));

    expect(await screen.findByText('That code is invalid or has expired')).toBeInTheDocument();
  });
});
