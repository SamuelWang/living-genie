import { useState } from 'react';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';
import { useTranslation } from 'react-i18next';
import { NavLink, Outlet, useNavigate } from 'react-router';

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
    <div className="flex h-screen flex-col bg-background text-foreground">
      <header className="flex items-center justify-between border-b p-4">
        <div className="flex items-center gap-6">
          <span className="font-semibold">{t('app.name')}</span>
          {user && (
            <nav className="flex items-center gap-4">
              <NavLink
                to="/diaries"
                className={({ isActive }) =>
                  cn('text-sm font-medium hover:underline', isActive ? 'text-foreground font-semibold' : 'text-muted-foreground')
                }
              >
                {t('nav.diaries')}
              </NavLink>
              <NavLink
                to="/todos"
                className={({ isActive }) =>
                  cn('text-sm font-medium hover:underline', isActive ? 'text-foreground font-semibold' : 'text-muted-foreground')
                }
              >
                {t('nav.todos')}
              </NavLink>
              <NavLink
                to="/genie"
                className={({ isActive }) =>
                  cn('text-sm font-medium hover:underline', isActive ? 'text-foreground font-semibold' : 'text-muted-foreground')
                }
              >
                {t('nav.genie')}
              </NavLink>
            </nav>
          )}
        </div>
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          {user && (
            <Button variant="outline" size="sm" onClick={() => void handleLogout()} disabled={isLoggingOut}>
              {t('nav.logout')}
            </Button>
          )}
        </div>
      </header>
      <main className="flex-1 min-h-0 overflow-y-auto p-4">
        <Outlet />
      </main>
    </div>
  );
}
