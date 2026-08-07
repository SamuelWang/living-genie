import { Link, useNavigate, useParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { DeleteTodoDialog } from '@/components/todo/DeleteTodoDialog';
import { getTodo, updateTodo } from '@/api/todos';
import { ApiError } from '@/api/errors';
import { formatEntryDate } from '@/lib/date';
import { toast } from '@/lib/toast';

export function TodoDetailPage() {
  const { t, i18n } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const {
    data: todo,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['todos', id],
    queryFn: () => getTodo(id!),
    enabled: !!id,
    retry: false,
  });

  const toggleMutation = useMutation({
    mutationFn: (completed: boolean) => updateTodo(id!, { completed }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['todos'] });
      toast.success(t('todo.updateSuccess'));
    },
    onError: () => toast.error(t('common.genericError')),
  });

  if (isLoading) {
    return <p className="text-muted-foreground text-sm">{t('common.loading')}</p>;
  }

  if (error) {
    if (error instanceof ApiError && error.status === 404) {
      return (
        <div className="flex flex-col gap-2">
          <p className="text-muted-foreground text-sm">{t('todo.todoNotFound')}</p>
          <Link to="/todos" className="text-primary text-sm underline underline-offset-4">
            {t('todo.detailBackToList')}
          </Link>
        </div>
      );
    }
    return <p className="text-destructive text-sm">{t('common.genericError')}</p>;
  }

  if (!todo) return null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <Checkbox
          checked={todo.completed}
          onCheckedChange={(checked) => toggleMutation.mutate(checked === true)}
          aria-label={t('todo.completedLabel')}
        />
        <div>
          <h1 className="text-2xl font-semibold">{todo.title}</h1>
          {todo.due_date && (
            <p className="text-muted-foreground text-sm">
              {formatEntryDate(todo.due_date, i18n.resolvedLanguage)}
            </p>
          )}
        </div>
      </div>

      {todo.description && <p className="whitespace-pre-wrap text-sm">{todo.description}</p>}

      <div className="flex items-center gap-2">
        <Button variant="outline" render={<Link to="/todos" />} nativeButton={false}>
          {t('todo.detailBackToList')}
        </Button>
        <Button variant="outline" render={<Link to={`/todos/${todo.id}/edit`} />} nativeButton={false}>
          {t('todo.editButton')}
        </Button>
        <DeleteTodoDialog todoId={todo.id} todoTitle={todo.title} onDeleted={() => navigate('/todos')} />
      </div>
    </div>
  );
}
