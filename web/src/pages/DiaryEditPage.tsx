import { Link, useNavigate, useParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { DiaryEntryForm, type DiaryEntryFormValues } from '@/components/diary/DiaryEntryForm';
import { getDiaryEntry, updateDiaryEntry } from '@/api/diaries';
import { ApiError } from '@/api/errors';

export function DiaryEditPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

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

  const updateMutation = useMutation({
    mutationFn: (values: DiaryEntryFormValues) => updateDiaryEntry(id!, values),
    onSuccess: (updatedEntry) => {
      queryClient.setQueryData(['diaries', id], updatedEntry);
      void queryClient.invalidateQueries({ queryKey: ['diaries'] });
      void navigate(`/diaries/${id}`);
    },
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
      <h1 className="text-2xl font-semibold">{t('diary.editTitle')}</h1>
      <DiaryEntryForm
        key={entry.id}
        initialValues={{ title: entry.title, entry_date: entry.entry_date, content: entry.content }}
        submitLabel="diary.editSubmit"
        submitting={updateMutation.isPending}
        errorMessage={updateMutation.isError ? t('common.genericError') : null}
        onSubmit={(values) => updateMutation.mutate(values)}
        onCancel={() => void navigate(`/diaries/${id}`)}
      />
    </div>
  );
}
