import { useTranslation } from 'react-i18next';

export function DiaryCreatePage() {
  const { t } = useTranslation();
  return <h1 className="text-2xl font-semibold">{t('diary.createTitle')}</h1>;
}
