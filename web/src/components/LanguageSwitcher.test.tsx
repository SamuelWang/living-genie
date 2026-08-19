import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import i18n from '@/i18n/config';
import { renderWithProviders } from '@/test/render';
import { getMe } from '@/api/auth';
import { LanguageSwitcher } from './LanguageSwitcher';

vi.mock('@/api/auth');

const mockGetMe = vi.mocked(getMe);

const STORAGE_KEY = 'living-genie-language';

describe('LanguageSwitcher', () => {
  beforeEach(() => {
    mockGetMe.mockResolvedValue(null);
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
