import { useParams } from 'react-router';
import { useTranslation } from 'react-i18next';

export function DiaryDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  return (
    <div>
      <h1 className="text-2xl font-semibold">{t('diary.detailTitle')}</h1>
      <p className="text-sm text-muted-foreground">{id}</p>
    </div>
  );
}
