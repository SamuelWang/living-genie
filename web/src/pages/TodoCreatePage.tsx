import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';

import { TodoForm, type TodoFormValues } from '@/components/todo/TodoForm';
import { createTodo } from '@/api/todos';

export function TodoCreatePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: createTodo,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['todos'] });
      void navigate('/todos');
    },
  });

  const handleSubmit = (values: TodoFormValues) => {
    createMutation.mutate(values);
  };

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t('todo.createTitle')}</h1>
      <TodoForm
        submitLabel="todo.createSubmit"
        submitting={createMutation.isPending}
        errorMessage={createMutation.isError ? t('common.genericError') : null}
        onSubmit={handleSubmit}
        onCancel={() => void navigate('/todos')}
      />
    </div>
  );
}
