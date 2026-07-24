import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router';

import { Button } from '@/components/ui/button';
import { listDiaryEntries } from '@/api/diaries';
import { formatEntryDate } from '@/lib/date';

export function DiaryListPage() {
  const { t, i18n } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['diaries'],
    queryFn: listDiaryEntries,
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t('diary.listTitle')}</h1>
        <Button render={<Link to="/diaries/new" />} nativeButton={false}>
          {t('diary.newEntryButton')}
        </Button>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">{t('common.loading')}</p>}
      {isError && <p className="text-destructive text-sm">{t('common.genericError')}</p>}

      {data && data.length === 0 && (
        <p className="text-muted-foreground text-sm">{t('diary.emptyState')}</p>
      )}

      {data && data.length > 0 && (
        <ul className="divide-border border-border divide-y rounded-md border">
          {data.map((entry) => (
            <li key={entry.id}>
              <Link
                to={`/diaries/${entry.id}`}
                className="hover:bg-muted flex items-center justify-between p-3"
              >
                <span className="font-medium">{entry.title}</span>
                <span className="text-muted-foreground text-sm">
                  {formatEntryDate(entry.entry_date, i18n.resolvedLanguage)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
