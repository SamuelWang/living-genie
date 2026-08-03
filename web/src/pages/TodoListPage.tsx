import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { listTodos, updateTodo } from '@/api/todos';
import { formatEntryDate } from '@/lib/date';
import { cn } from '@/lib/utils';

type TodoFilter = 'all' | 'pending' | 'completed';

const TODO_FILTERS: TodoFilter[] = ['all', 'pending', 'completed'];

export function TodoListPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<TodoFilter>('all');
  const completed = filter === 'all' ? undefined : filter === 'completed';
  const { data, isLoading, isError } = useQuery({
    queryKey: ['todos', filter],
    queryFn: () => listTodos(completed),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, completed }: { id: string; completed: boolean }) =>
      updateTodo(id, { completed }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['todos'] });
    },
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t('todo.listTitle')}</h1>
        <Button render={<Link to="/todos/new" />} nativeButton={false}>
          {t('todo.newTodoButton')}
        </Button>
      </div>

      <div className="flex gap-1">
        {TODO_FILTERS.map((value) => (
          <Button
            key={value}
            size="sm"
            variant={filter === value ? 'secondary' : 'ghost'}
            aria-pressed={filter === value}
            onClick={() => setFilter(value)}
          >
            {t(`todo.filter.${value}`)}
          </Button>
        ))}
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">{t('common.loading')}</p>}
      {isError && <p className="text-destructive text-sm">{t('common.genericError')}</p>}

      {data && data.length === 0 && (
        <p className="text-muted-foreground text-sm">
          {t(filter === 'all' ? 'todo.emptyState' : 'todo.emptyStateFiltered')}
        </p>
      )}

      {data && data.length > 0 && (
        <ul className="divide-border border-border divide-y rounded-md border">
          {data.map((todo) => (
            <li key={todo.id} className="flex items-center gap-3 p-3">
              <Checkbox
                checked={todo.completed}
                onCheckedChange={(checked) =>
                  toggleMutation.mutate({ id: todo.id, completed: checked === true })
                }
                aria-label={t('todo.completedLabel')}
              />
              <Link
                to={`/todos/${todo.id}`}
                className="hover:bg-muted flex flex-1 items-center justify-between"
              >
                <span className={cn('font-medium', todo.completed && 'text-muted-foreground line-through')}>
                  {todo.title}
                </span>
                {todo.due_date && (
                  <span className="text-muted-foreground text-sm">
                    {formatEntryDate(todo.due_date, i18n.resolvedLanguage)}
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
