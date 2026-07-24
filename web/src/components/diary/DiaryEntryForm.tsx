import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { DiaryEditor } from '@/components/editor/DiaryEditor';
import { todayLocalISODate } from '@/lib/date';

export interface DiaryEntryFormValues {
  title: string;
  entry_date: string;
  content: string;
}

interface DiaryEntryFormProps {
  initialValues?: DiaryEntryFormValues;
  submitLabel: string;
  submitting: boolean;
  errorMessage?: string | null;
  onSubmit: (values: DiaryEntryFormValues) => void;
}

export function DiaryEntryForm({
  initialValues,
  submitLabel,
  submitting,
  errorMessage,
  onSubmit,
}: DiaryEntryFormProps) {
  const { t } = useTranslation();
  const [title, setTitle] = useState(initialValues?.title ?? '');
  const [entryDate, setEntryDate] = useState(initialValues?.entry_date ?? todayLocalISODate());
  const [content, setContent] = useState(initialValues?.content ?? '');
  const [touched, setTouched] = useState(false);

  const titleValid = title.trim().length > 0;
  const dateValid = entryDate.length > 0;
  const isValid = titleValid && dateValid;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setTouched(true);
    if (!isValid) return;
    onSubmit({ title: title.trim(), entry_date: entryDate, content });
  };

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="diary-title">{t('diary.titleLabel')}</Label>
        <Input
          id="diary-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          aria-invalid={touched && !titleValid}
        />
        {touched && !titleValid && (
          <p role="alert" className="text-destructive text-xs">
            {t('diary.titleRequired')}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="diary-entry-date">{t('diary.entryDateLabel')}</Label>
        <Input
          id="diary-entry-date"
          type="date"
          value={entryDate}
          onChange={(e) => setEntryDate(e.target.value)}
          aria-invalid={touched && !dateValid}
          className="w-auto"
        />
        {touched && !dateValid && (
          <p role="alert" className="text-destructive text-xs">
            {t('diary.entryDateRequired')}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label>{t('diary.contentLabel')}</Label>
        <DiaryEditor content={content} onChange={setContent} />
      </div>

      {errorMessage && (
        <p role="alert" className="text-destructive text-sm">
          {errorMessage}
        </p>
      )}

      <div>
        <Button type="submit" disabled={submitting}>
          {t(submitLabel)}
        </Button>
      </div>
    </form>
  );
}
