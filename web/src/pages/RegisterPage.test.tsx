import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import { renderWithProviders } from '@/test/render';
import { RegisterPage } from './RegisterPage';
import { register } from '@/api/auth';
import { ApiError } from '@/api/errors';

vi.mock('@/api/auth');

const mockRegister = vi.mocked(register);

function renderRegisterPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/login" element={<div>Login page</div>} />
    </Routes>,
    { route: '/register', withAuthProvider: false },
  );
}

describe('RegisterPage', () => {
  it('shows required-field alerts on empty submit', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await user.click(screen.getByRole('button', { name: 'Register' }));

    expect(await screen.findByText('Email is required')).toBeInTheDocument();
    expect(screen.getByText('Password is required')).toBeInTheDocument();
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it('shows an invalid-format alert for a malformed email', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await user.type(screen.getByLabelText('Email'), 'not-an-email');
    await user.type(screen.getByLabelText('Password'), 'longenoughpassword');
    await user.click(screen.getByRole('button', { name: 'Register' }));

    expect(await screen.findByText('Enter a valid email address')).toBeInTheDocument();
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it('shows a too-short alert for a short password', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await user.type(screen.getByLabelText('Email'), 'user@example.com');
    await user.type(screen.getByLabelText('Password'), 'short');
    await user.click(screen.getByRole('button', { name: 'Register' }));

    expect(await screen.findByText('Password must be at least 8 characters')).toBeInTheDocument();
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it('shows a duplicate-email message on 409 without confirming other emails', async () => {
    const user = userEvent.setup();
    mockRegister.mockRejectedValue(new ApiError(409, 'conflict'));
    renderRegisterPage();

    await user.type(screen.getByLabelText('Email'), 'taken@example.com');
    await user.type(screen.getByLabelText('Password'), 'longenoughpassword');
    await user.click(screen.getByRole('button', { name: 'Register' }));

    expect(
      await screen.findByText('An account with this email already exists'),
    ).toBeInTheDocument();
  });

  it('navigates to /login on success (no auto-login)', async () => {
    const user = userEvent.setup();
    mockRegister.mockResolvedValue({ id: '1', email: 'user@example.com', created_at: '2026-01-01' });
    renderRegisterPage();

    await user.type(screen.getByLabelText('Email'), 'user@example.com');
    await user.type(screen.getByLabelText('Password'), 'longenoughpassword');
    await user.click(screen.getByRole('button', { name: 'Register' }));

    await waitFor(() => expect(screen.getByText('Login page')).toBeInTheDocument());
  });
});
