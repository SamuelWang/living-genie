import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { useTranslation } from 'react-i18next';
import { Outlet } from 'react-router';

export function RootLayout() {
  const { t } = useTranslation();
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="flex items-center justify-between border-b p-4">
        <span className="font-semibold">{t('app.name')}</span>
        <LanguageSwitcher />
      </header>
      <main className="p-4">
        <Outlet />
      </main>
    </div>
  );
}
