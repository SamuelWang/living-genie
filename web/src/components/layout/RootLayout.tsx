import { useState } from 'react';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';
import { useTranslation } from 'react-i18next';
import { Outlet, useNavigate } from 'react-router';

export function RootLayout() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      void navigate('/login', { replace: true });
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="flex items-center justify-between border-b p-4">
        <span className="font-semibold">{t('app.name')}</span>
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          {user && (
            <Button variant="outline" size="sm" onClick={() => void handleLogout()} disabled={isLoggingOut}>
              {t('nav.logout')}
            </Button>
          )}
        </div>
      </header>
      <main className="p-4">
        <Outlet />
      </main>
    </div>
  );
}
