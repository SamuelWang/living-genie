import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { deleteTodo } from '@/api/todos';
import { toast } from '@/lib/toast';

interface DeleteTodoDialogProps {
  todoId: string;
  todoTitle: string;
  onDeleted?: () => void;
}

export function DeleteTodoDialog({ todoId, todoTitle, onDeleted }: DeleteTodoDialogProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => deleteTodo(todoId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['todos'] });
      setOpen(false);
      toast.success(t('todo.deleteSuccess'));
      onDeleted?.();
    },
    onError: () => toast.error(t('common.genericError')),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="destructive" size="sm" />}>
        {t('todo.deleteButton')}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('todo.deleteConfirmTitle')}</DialogTitle>
          <DialogDescription>
            {t('todo.deleteConfirmDescription', { title: todoTitle })}
          </DialogDescription>
        </DialogHeader>
        {deleteMutation.isError && (
          <p role="alert" className="text-destructive text-sm">
            {t('common.genericError')}
          </p>
        )}
        <DialogFooter>
          <DialogClose render={<Button variant="outline" />}>{t('common.cancel')}</DialogClose>
          <Button
            variant="destructive"
            onClick={() => deleteMutation.mutate()}
            disabled={deleteMutation.isPending}
          >
            {t('todo.deleteConfirmAction')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
