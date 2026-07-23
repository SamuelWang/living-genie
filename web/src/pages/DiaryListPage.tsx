import { useTranslation } from 'react-i18next';

export function DiaryListPage() {
  const { t } = useTranslation();
  return <h1 className="text-2xl font-semibold">{t('diary.listTitle')}</h1>;
}
