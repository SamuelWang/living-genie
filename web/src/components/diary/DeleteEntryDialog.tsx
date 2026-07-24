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
import { deleteDiaryEntry } from '@/api/diaries';

interface DeleteEntryDialogProps {
  entryId: string;
  entryTitle: string;
  onDeleted?: () => void;
}

export function DeleteEntryDialog({ entryId, entryTitle, onDeleted }: DeleteEntryDialogProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => deleteDiaryEntry(entryId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['diaries'] });
      setOpen(false);
      onDeleted?.();
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="destructive" size="sm" />}>
        {t('diary.deleteButton')}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('diary.deleteConfirmTitle')}</DialogTitle>
          <DialogDescription>
            {t('diary.deleteConfirmDescription', { title: entryTitle })}
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
            {t('diary.deleteConfirmAction')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
