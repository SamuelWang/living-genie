import { Link, useNavigate, useParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { DiaryEditor } from '@/components/editor/DiaryEditor';
import { DeleteEntryDialog } from '@/components/diary/DeleteEntryDialog';
import { getDiaryEntry } from '@/api/diaries';
import { ApiError } from '@/api/errors';
import { formatEntryDate } from '@/lib/date';

export function DiaryDetailPage() {
  const { t, i18n } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const {
    data: entry,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['diaries', id],
    queryFn: () => getDiaryEntry(id!),
    enabled: !!id,
    retry: false,
  });

  if (isLoading) {
    return <p className="text-muted-foreground text-sm">{t('common.loading')}</p>;
  }

  if (error) {
    if (error instanceof ApiError && error.status === 404) {
      return (
        <div className="flex flex-col gap-2">
          <p className="text-muted-foreground text-sm">{t('diary.entryNotFound')}</p>
          <Link to="/diaries" className="text-primary text-sm underline underline-offset-4">
            {t('diary.detailBackToList')}
          </Link>
        </div>
      );
    }
    return <p className="text-destructive text-sm">{t('common.genericError')}</p>;
  }

  if (!entry) return null;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold">{entry.title}</h1>
        <p className="text-muted-foreground text-sm">
          {formatEntryDate(entry.entry_date, i18n.resolvedLanguage)}
        </p>
      </div>

      <DiaryEditor key={entry.id} content={entry.content} onChange={() => {}} editable={false} />

      <div className="flex items-center gap-2">
        <Button variant="outline" render={<Link to="/diaries" />} nativeButton={false}>
          {t('diary.detailBackToList')}
        </Button>
        <Button
          variant="outline"
          render={<Link to={`/diaries/${entry.id}/edit`} />}
          nativeButton={false}
        >
          {t('diary.editButton')}
        </Button>
        <DeleteEntryDialog
          entryId={entry.id}
          entryTitle={entry.title}
          onDeleted={() => navigate('/diaries')}
        />
      </div>
    </div>
  );
}
