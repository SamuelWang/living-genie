import { EditorContent, useEditor } from '@tiptap/react';
import { Markdown } from '@tiptap/markdown';
import StarterKit from '@tiptap/starter-kit';
import { TaskItem } from '@tiptap/extension-task-item';
import { TaskList } from '@tiptap/extension-task-list';
import { Table } from '@tiptap/extension-table';
import { TableCell } from '@tiptap/extension-table-cell';
import { TableHeader } from '@tiptap/extension-table-header';
import { TableRow } from '@tiptap/extension-table-row';
import { Color, FontFamily, FontSize } from '@tiptap/extension-text-style';
import { Image } from '@tiptap/extension-image';
import { TextAlign } from '@tiptap/extension-text-align';
import type { ClipboardEvent, DragEvent } from 'react';

import { AlignedHeading, AlignedParagraph, StyledTextStyle } from './extensions';
import { EditorToolbar } from './EditorToolbar';
import { useImageUpload } from './useImageUpload';
import './editor.css';

interface DiaryEditorProps {
  /** Initial markdown content. Tiptap only reads this on mount — to load a different entry,
   * remount the component (e.g. `key={entryId}`) rather than changing this prop in place. */
  content: string;
  onChange: (markdown: string) => void;
  editable?: boolean;
}

function isImageFile(file: File | undefined | null): file is File {
  return !!file && file.type.startsWith('image/');
}

export function DiaryEditor({ content, onChange, editable = true }: DiaryEditorProps) {
  const { insertImage, isUploading, uploadError } = useImageUpload();
  const editor = useEditor({
    editable,
    extensions: [
      StarterKit.configure({ heading: false, paragraph: false }),
      AlignedHeading,
      AlignedParagraph,
      Markdown.configure({ markedOptions: { gfm: true } }),
      TaskList,
      TaskItem,
      Table,
      TableRow,
      TableHeader,
      TableCell,
      StyledTextStyle,
      Color,
      FontFamily,
      FontSize,
      Image,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
    ],
    content,
    contentType: 'markdown',
    onUpdate: ({ editor: updatedEditor }) => onChange(updatedEditor.getMarkdown()),
  });

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    const file = event.dataTransfer.files[0];
    if (!isImageFile(file) || !editor) return;
    event.preventDefault();
    const pos = editor.view.posAtCoords({ left: event.clientX, top: event.clientY })?.pos;
    void insertImage(editor, file, pos);
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    if (Array.from(event.dataTransfer.items).some((item) => item.type.startsWith('image/'))) {
      event.preventDefault();
    }
  };

  const handlePaste = (event: ClipboardEvent<HTMLDivElement>) => {
    const file = event.clipboardData.files[0];
    if (!isImageFile(file) || !editor) return;
    event.preventDefault();
    void insertImage(editor, file);
  };

  return (
    <div className="border-border overflow-hidden rounded-md border">
      {editable && (
        <EditorToolbar
          editor={editor}
          onInsertImage={(file) => editor && void insertImage(editor, file)}
          isUploadingImage={isUploading}
        />
      )}
      <div
        onDrop={editable ? handleDrop : undefined}
        onDragOver={editable ? handleDragOver : undefined}
        onPaste={editable ? handlePaste : undefined}
      >
        <EditorContent editor={editor} />
      </div>
      {editable && uploadError && (
        <p role="alert" className="text-destructive border-border border-t p-2 text-xs">
          {uploadError}
        </p>
      )}
    </div>
  );
}
