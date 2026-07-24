import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';

import { DiaryEntryForm, type DiaryEntryFormValues } from '@/components/diary/DiaryEntryForm';
import { createDiaryEntry } from '@/api/diaries';

export function DiaryCreatePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: createDiaryEntry,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['diaries'] });
      void navigate('/diaries');
    },
  });

  const handleSubmit = (values: DiaryEntryFormValues) => {
    createMutation.mutate(values);
  };

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t('diary.createTitle')}</h1>
      <DiaryEntryForm
        submitLabel="diary.createSubmit"
        submitting={createMutation.isPending}
        errorMessage={createMutation.isError ? t('common.genericError') : null}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
