import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

export interface TodoFormValues {
  title: string;
  description: string;
  due_date: string | null;
}

interface TodoFormProps {
  initialValues?: TodoFormValues;
  submitLabel: string;
  submitting: boolean;
  errorMessage?: string | null;
  onSubmit: (values: TodoFormValues) => void;
  onCancel?: () => void;
}

export function TodoForm({
  initialValues,
  submitLabel,
  submitting,
  errorMessage,
  onSubmit,
  onCancel,
}: TodoFormProps) {
  const { t } = useTranslation();
  const [title, setTitle] = useState(initialValues?.title ?? '');
  const [description, setDescription] = useState(initialValues?.description ?? '');
  const [dueDate, setDueDate] = useState(initialValues?.due_date ?? '');
  const [touched, setTouched] = useState(false);

  const titleValid = title.trim().length > 0;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setTouched(true);
    if (!titleValid) return;
    onSubmit({ title: title.trim(), description, due_date: dueDate.length > 0 ? dueDate : null });
  };

  return (
    <form className="flex flex-col gap-4" noValidate onSubmit={handleSubmit}>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="todo-title">{t('todo.titleLabel')}</Label>
        <Input
          id="todo-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          aria-invalid={touched && !titleValid}
        />
        {touched && !titleValid && (
          <p role="alert" className="text-destructive text-xs">
            {t('todo.titleRequired')}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="todo-due-date">{t('todo.dueDateLabel')}</Label>
        <Input
          id="todo-due-date"
          type="date"
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
          className="w-auto"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="todo-description">{t('todo.descriptionLabel')}</Label>
        <Textarea
          id="todo-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>

      {errorMessage && (
        <p role="alert" className="text-destructive text-sm">
          {errorMessage}
        </p>
      )}

      <div className="flex gap-2">
        <Button type="submit" disabled={submitting}>
          {t(submitLabel)}
        </Button>
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            {t('common.cancel')}
          </Button>
        )}
      </div>
    </form>
  );
}
