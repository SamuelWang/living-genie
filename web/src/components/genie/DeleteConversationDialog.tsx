import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Trash2Icon } from 'lucide-react';

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
import { deleteConversation } from '@/api/conversations';

interface DeleteConversationDialogProps {
  conversationId: string;
  conversationPreview: string | null;
  onDeleted?: () => void;
}

export function DeleteConversationDialog({
  conversationId,
  conversationPreview,
  onDeleted,
}: DeleteConversationDialogProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => deleteConversation(conversationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['conversations'] });
      setOpen(false);
      onDeleted?.();
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="destructive" size="icon-sm" />}>
        <Trash2Icon />
        <span className="sr-only">{t('genie.deleteButton')}</span>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('genie.deleteConfirmTitle')}</DialogTitle>
          <DialogDescription>
            {t('genie.deleteConfirmDescription', {
              preview: conversationPreview ?? t('genie.noPreview'),
            })}
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
            {t('genie.deleteConfirmAction')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
