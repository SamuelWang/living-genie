import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import { renderWithProviders } from '@/test/render';
import { ForgotPasswordPage } from './ForgotPasswordPage';
import { forgotPassword, getMe } from '@/api/auth';
import { ApiError } from '@/api/errors';

vi.mock('@/api/auth');

const mockGetMe = vi.mocked(getMe);
const mockForgotPassword = vi.mocked(forgotPassword);

function renderForgotPasswordPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
    </Routes>,
    { route: '/forgot-password' },
  );
}

describe('ForgotPasswordPage', () => {
  beforeEach(() => {
    mockGetMe.mockResolvedValue(null);
  });

  it('shows a required-email alert on empty submit and does not call forgotPassword', async () => {
    const user = userEvent.setup();
    renderForgotPasswordPage();

    await user.click(screen.getByRole('button', { name: 'Send reset code' }));

    expect(await screen.findByText('Email is required')).toBeInTheDocument();
    expect(mockForgotPassword).not.toHaveBeenCalled();
  });

  it('shows the submitted view and reset-password link when the request succeeds', async () => {
    const user = userEvent.setup();
    mockForgotPassword.mockResolvedValue(undefined);
    renderForgotPasswordPage();

    await user.type(screen.getByLabelText('Email'), 'user@example.com');
    await user.click(screen.getByRole('button', { name: 'Send reset code' }));

    expect(mockForgotPassword).toHaveBeenCalledWith(
      { email: 'user@example.com' },
      expect.anything(),
    );
    expect(
      await screen.findByText(
        "If that email is registered, we've sent a code to reset your password.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Reset password' })).toHaveAttribute(
      'href',
      '/reset-password?email=user%40example.com',
    );
  });

  it('shows the identical submitted view even when the request fails (no enumeration leak)', async () => {
    const user = userEvent.setup();
    mockForgotPassword.mockRejectedValue(new ApiError(500, 'boom'));
    renderForgotPasswordPage();

    await user.type(screen.getByLabelText('Email'), 'user@example.com');
    await user.click(screen.getByRole('button', { name: 'Send reset code' }));

    expect(
      await screen.findByText(
        "If that email is registered, we've sent a code to reset your password.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Reset password' })).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
