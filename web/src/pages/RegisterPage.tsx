import { useTranslation } from 'react-i18next';

export function RegisterPage() {
  const { t } = useTranslation();
  return <h1 className="text-2xl font-semibold">{t('auth.registerTitle')}</h1>;
}
