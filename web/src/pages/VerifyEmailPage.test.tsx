import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import { renderWithProviders } from '@/test/render';
import { VerifyEmailPage } from './VerifyEmailPage';
import { getMe, resendVerification, verifyEmail } from '@/api/auth';
import { ApiError } from '@/api/errors';
import { useAuth } from '@/hooks/useAuth';

vi.mock('@/api/auth');

const mockGetMe = vi.mocked(getMe);
const mockVerifyEmail = vi.mocked(verifyEmail);
const mockResendVerification = vi.mocked(resendVerification);

function DiariesStub() {
  const { user } = useAuth();
  return <div>Diaries page — {user?.email}</div>;
}

function renderVerifyEmailPage(route = '/verify-email') {
  return renderWithProviders(
    <Routes>
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/diaries" element={<DiariesStub />} />
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

describe('VerifyEmailPage', () => {
  beforeEach(() => {
    mockGetMe.mockResolvedValue(null);
  });

  it('pre-fills and locks the email field when provided via query param', () => {
    renderVerifyEmailPage('/verify-email?email=user%40example.com');

    const emailInput = screen.getByLabelText('Email');
    expect(emailInput).toHaveValue('user@example.com');
    expect(emailInput).toHaveAttribute('readonly');
  });

  it('shows required-field alerts on empty submit and does not call verifyEmail', async () => {
    const user = userEvent.setup();
    renderVerifyEmailPage();

    await user.click(screen.getByRole('button', { name: 'Verify' }));

    expect(await screen.findByText('Email is required')).toBeInTheDocument();
    expect(screen.getByText('Verification code is required')).toBeInTheDocument();
    expect(mockVerifyEmail).not.toHaveBeenCalled();
  });

  it('updates the auth cache and navigates to /diaries on success', async () => {
    const user = userEvent.setup();
    mockVerifyEmail.mockResolvedValue(fullUser);
    renderVerifyEmailPage('/verify-email?email=user%40example.com');

    await user.type(screen.getByLabelText('Verification code'), 'ABCD1234');
    await user.click(screen.getByRole('button', { name: 'Verify' }));

    await waitFor(() =>
      expect(screen.getByText('Diaries page — user@example.com')).toBeInTheDocument(),
    );
  });

  it('shows a generic invalid-or-expired-code message on error', async () => {
    const user = userEvent.setup();
    mockVerifyEmail.mockRejectedValue(new ApiError(400, 'Invalid or expired code'));
    renderVerifyEmailPage('/verify-email?email=user%40example.com');

    await user.type(screen.getByLabelText('Verification code'), 'WRONGCOD');
    await user.click(screen.getByRole('button', { name: 'Verify' }));

    expect(await screen.findByText('That code is invalid or has expired')).toBeInTheDocument();
  });

  it('resends the verification code', async () => {
    const user = userEvent.setup();
    mockResendVerification.mockResolvedValue(undefined);
    renderVerifyEmailPage('/verify-email?email=user%40example.com');

    await user.click(screen.getByRole('button', { name: 'Resend code' }));

    await waitFor(() =>
      expect(mockResendVerification).toHaveBeenCalledWith(
        { email: 'user@example.com' },
        expect.anything(),
      ),
    );
  });
});
