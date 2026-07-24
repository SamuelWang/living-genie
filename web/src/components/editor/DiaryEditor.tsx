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

import { AlignedHeading, AlignedParagraph, StyledTextStyle } from './extensions';
import { EditorToolbar } from './EditorToolbar';
import './editor.css';

interface DiaryEditorProps {
  /** Initial markdown content. Tiptap only reads this on mount — to load a different entry,
   * remount the component (e.g. `key={entryId}`) rather than changing this prop in place. */
  content: string;
  onChange: (markdown: string) => void;
  editable?: boolean;
}

export function DiaryEditor({ content, onChange, editable = true }: DiaryEditorProps) {
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

  return (
    <div className="border-border overflow-hidden rounded-md border">
      <EditorToolbar editor={editor} />
      <EditorContent editor={editor} />
    </div>
  );
}
