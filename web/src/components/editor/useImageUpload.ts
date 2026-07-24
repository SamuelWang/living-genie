import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import type { Editor } from '@tiptap/core';
import { uploadImage } from '@/api/uploads';

const API_URL = import.meta.env.VITE_API_URL as string;

export function useImageUpload() {
  const { t } = useTranslation();
  const mutation = useMutation({ mutationFn: uploadImage });

  const insertImage = useCallback(
    async (editor: Editor, file: File, pos?: number) => {
      const { url } = await mutation.mutateAsync(file);
      const absoluteUrl = `${API_URL}${url}`;
      const chain = editor.chain().focus();
      if (pos !== undefined) {
        chain.insertContentAt(pos, { type: 'image', attrs: { src: absoluteUrl } });
      } else {
        chain.setImage({ src: absoluteUrl });
      }
      chain.run();
    },
    [mutation],
  );

  return {
    insertImage,
    isUploading: mutation.isPending,
    uploadError: mutation.isError ? t('editor.uploadError') : null,
  };
}
