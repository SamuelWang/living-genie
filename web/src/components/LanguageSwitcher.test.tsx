import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import i18n from '@/i18n/config';
import { renderWithProviders } from '@/test/render';
import { getMe, updateLocale } from '@/api/auth';
import { useAuth } from '@/hooks/useAuth';
import { LanguageSwitcher } from './LanguageSwitcher';

vi.mock('@/api/auth');

const mockGetMe = vi.mocked(getMe);
const mockUpdateLocale = vi.mocked(updateLocale);

const STORAGE_KEY = 'living-genie-language';

function AuthProbe() {
  const { user, isLoading } = useAuth();
  return <div>{isLoading ? 'loading' : user ? 'signed-in' : 'signed-out'}</div>;
}

describe('LanguageSwitcher', () => {
  beforeEach(() => {
    mockGetMe.mockResolvedValue(null);
    mockUpdateLocale.mockClear();
  });

  afterEach(async () => {
    localStorage.removeItem(STORAGE_KEY);
    await i18n.changeLanguage('zh-Hant');
  });

  it('switches the rendered language and persists the choice to localStorage', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LanguageSwitcher />);

    await user.click(screen.getByRole('button', { name: 'EN' }));

    expect(i18n.resolvedLanguage).toBe('en');
    expect(localStorage.getItem(STORAGE_KEY)).toBe('en');
    expect(mockUpdateLocale).not.toHaveBeenCalled();
  });

  it('calls updateLocale with the new locale when signed in', async () => {
    const user = userEvent.setup();
    mockGetMe.mockResolvedValue({
      id: '1',
      email: 'user@example.com',
      locale: 'zh-Hant',
      created_at: '2026-01-01',
      email_verified: true,
    });
    mockUpdateLocale.mockResolvedValue({
      id: '1',
      email: 'user@example.com',
      locale: 'en',
      created_at: '2026-01-01',
      email_verified: true,
    });
    renderWithProviders(
      <>
        <AuthProbe />
        <LanguageSwitcher />
      </>,
    );

    await screen.findByText('signed-in');
    await user.click(screen.getByRole('button', { name: 'EN' }));

    expect(mockUpdateLocale).toHaveBeenCalledWith({ locale: 'en' }, expect.anything());
  });

  it('honors a persisted preference when the i18n instance re-initializes (reload)', async () => {
    localStorage.setItem(STORAGE_KEY, 'en');
    vi.resetModules();

    const { default: freshI18n } = await import('@/i18n/config');
    if (!freshI18n.isInitialized) {
      await new Promise<void>((resolve) => freshI18n.on('initialized', () => resolve()));
    }

    expect(freshI18n.resolvedLanguage).toBe('en');
  });
});
