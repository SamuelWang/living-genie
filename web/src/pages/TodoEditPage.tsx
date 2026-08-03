import { Link, useNavigate, useParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { TodoForm, type TodoFormValues } from '@/components/todo/TodoForm';
import { getTodo, updateTodo } from '@/api/todos';
import { ApiError } from '@/api/errors';

export function TodoEditPage() {
  const { t } = useTranslation();
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

  const updateMutation = useMutation({
    mutationFn: (values: TodoFormValues) => updateTodo(id!, values),
    onSuccess: (updatedTodo) => {
      queryClient.setQueryData(['todos', id], updatedTodo);
      void queryClient.invalidateQueries({ queryKey: ['todos'] });
      void navigate(`/todos/${id}`);
    },
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
      <h1 className="text-2xl font-semibold">{t('todo.editTitle')}</h1>
      <TodoForm
        key={todo.id}
        initialValues={{
          title: todo.title,
          description: todo.description ?? '',
          due_date: todo.due_date,
        }}
        submitLabel="todo.editSubmit"
        submitting={updateMutation.isPending}
        errorMessage={updateMutation.isError ? t('common.genericError') : null}
        onSubmit={(values) => updateMutation.mutate(values)}
        onCancel={() => void navigate(`/todos/${id}`)}
      />
    </div>
  );
}
