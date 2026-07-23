import { useTranslation } from 'react-i18next';

export function LoginPage() {
  const { t } = useTranslation();
  return <h1 className="text-2xl font-semibold">{t('auth.loginTitle')}</h1>;
}
