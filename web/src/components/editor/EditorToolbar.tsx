import type { Editor } from '@tiptap/core';
import { useEditorState } from '@tiptap/react';
import type { ReactNode } from 'react';
import { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlignCenter,
  AlignJustify,
  AlignLeft,
  AlignRight,
  Bold,
  Code,
  Code2,
  Heading1,
  Heading2,
  Heading3,
  Image as ImageIcon,
  Italic,
  Link2,
  List,
  ListOrdered,
  ListTodo,
  Minus,
  Quote,
  Redo2,
  Strikethrough,
  Table as TableIcon,
  Trash2,
  Undo2,
} from 'lucide-react';

import { Button } from '@/components/ui/button';

interface EditorToolbarProps {
  editor: Editor | null;
  onInsertImage?: (file: File) => void;
  isUploadingImage?: boolean;
}

function ToolbarButton({
  active,
  disabled,
  title,
  onClick,
  children,
}: {
  active?: boolean;
  disabled?: boolean;
  title: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <Button
      type="button"
      variant={active ? 'default' : 'ghost'}
      size="icon-sm"
      title={title}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </Button>
  );
}

const FONT_FAMILIES = [
  { labelKey: 'editor.toolbar.optionDefault', value: '' },
  { labelKey: 'editor.toolbar.fontSans', value: 'ui-sans-serif, system-ui, sans-serif' },
  { labelKey: 'editor.toolbar.fontSerif', value: 'ui-serif, Georgia, serif' },
  { labelKey: 'editor.toolbar.fontMono', value: 'ui-monospace, SFMono-Regular, monospace' },
];

const FONT_SIZES = [
  { label: null, value: '' },
  { label: '12', value: '12px' },
  { label: '14', value: '14px' },
  { label: '16', value: '16px' },
  { label: '18', value: '18px' },
  { label: '24', value: '24px' },
  { label: '32', value: '32px' },
];

export function EditorToolbar({ editor, onInsertImage, isUploadingImage }: EditorToolbarProps) {
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement>(null);
  // `editor.isActive(...)` reads live state but doesn't itself trigger a re-render — Tiptap's
  // `onUpdate` (which is what re-renders this component, via the parent's onChange) only fires
  // on content changes, not on cursor/selection moves. useEditorState subscribes to every
  // transaction (selection-only included) so button highlighting and the in-table controls stay
  // in sync when the user just clicks around without editing.
  const state = useEditorState({
    editor,
    selector: ({ editor: ed }) => {
      if (!ed) return null;
      return {
        heading1: ed.isActive('heading', { level: 1 }),
        heading2: ed.isActive('heading', { level: 2 }),
        heading3: ed.isActive('heading', { level: 3 }),
        bold: ed.isActive('bold'),
        italic: ed.isActive('italic'),
        strike: ed.isActive('strike'),
        code: ed.isActive('code'),
        link: ed.isActive('link'),
        bulletList: ed.isActive('bulletList'),
        orderedList: ed.isActive('orderedList'),
        taskList: ed.isActive('taskList'),
        blockquote: ed.isActive('blockquote'),
        codeBlock: ed.isActive('codeBlock'),
        alignLeft: ed.isActive({ textAlign: 'left' }),
        alignCenter: ed.isActive({ textAlign: 'center' }),
        alignRight: ed.isActive({ textAlign: 'right' }),
        alignJustify: ed.isActive({ textAlign: 'justify' }),
        inTable: ed.isActive('table'),
        color: (ed.getAttributes('textStyle').color as string | undefined) ?? '',
        fontFamily: (ed.getAttributes('textStyle').fontFamily as string | undefined) ?? '',
        fontSize: (ed.getAttributes('textStyle').fontSize as string | undefined) ?? '',
        canUndo: ed.can().undo(),
        canRedo: ed.can().redo(),
      };
    },
  });

  if (!editor || !state) return null;

  return (
    <div className="border-border bg-muted/40 flex flex-wrap items-center gap-1 border-b p-1">
      <ToolbarButton
        title={t('editor.toolbar.heading1')}
        active={state.heading1}
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
      >
        <Heading1 />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.heading2')}
        active={state.heading2}
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
      >
        <Heading2 />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.heading3')}
        active={state.heading3}
        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
      >
        <Heading3 />
      </ToolbarButton>

      <div className="bg-border mx-1 h-5 w-px" />

      <ToolbarButton
        title={t('editor.toolbar.bold')}
        active={state.bold}
        onClick={() => editor.chain().focus().toggleBold().run()}
      >
        <Bold />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.italic')}
        active={state.italic}
        onClick={() => editor.chain().focus().toggleItalic().run()}
      >
        <Italic />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.strikethrough')}
        active={state.strike}
        onClick={() => editor.chain().focus().toggleStrike().run()}
      >
        <Strikethrough />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.inlineCode')}
        active={state.code}
        onClick={() => editor.chain().focus().toggleCode().run()}
      >
        <Code />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.link')}
        active={state.link}
        onClick={() => {
          if (state.link) {
            editor.chain().focus().unsetLink().run();
            return;
          }
          const href = window.prompt('URL');
          if (href) editor.chain().focus().setLink({ href }).run();
        }}
      >
        <Link2 />
      </ToolbarButton>

      <div className="bg-border mx-1 h-5 w-px" />

      <ToolbarButton
        title={t('editor.toolbar.bulletList')}
        active={state.bulletList}
        onClick={() => editor.chain().focus().toggleBulletList().run()}
      >
        <List />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.orderedList')}
        active={state.orderedList}
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
      >
        <ListOrdered />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.taskList')}
        active={state.taskList}
        onClick={() => editor.chain().focus().toggleTaskList().run()}
      >
        <ListTodo />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.blockquote')}
        active={state.blockquote}
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
      >
        <Quote />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.codeBlock')}
        active={state.codeBlock}
        onClick={() => editor.chain().focus().toggleCodeBlock().run()}
      >
        <Code2 />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.horizontalRule')}
        onClick={() => editor.chain().focus().setHorizontalRule().run()}
      >
        <Minus />
      </ToolbarButton>

      <div className="bg-border mx-1 h-5 w-px" />

      <ToolbarButton
        title={t('editor.toolbar.alignLeft')}
        active={state.alignLeft}
        onClick={() => editor.chain().focus().setTextAlign('left').run()}
      >
        <AlignLeft />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.alignCenter')}
        active={state.alignCenter}
        onClick={() => editor.chain().focus().setTextAlign('center').run()}
      >
        <AlignCenter />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.alignRight')}
        active={state.alignRight}
        onClick={() => editor.chain().focus().setTextAlign('right').run()}
      >
        <AlignRight />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.justify')}
        active={state.alignJustify}
        onClick={() => editor.chain().focus().setTextAlign('justify').run()}
      >
        <AlignJustify />
      </ToolbarButton>

      <div className="bg-border mx-1 h-5 w-px" />

      <input
        type="color"
        title={t('editor.toolbar.textColor')}
        className="border-border h-7 w-7 cursor-pointer rounded border p-0.5"
        // Native color inputs can't represent "no color set" the way the font-family/size
        // <select>s show a "Default" option — black is the fallback swatch shown at the cursor
        // when there's no color mark there.
        value={state.color || '#000000'}
        onChange={(e) => editor.chain().focus().setColor(e.target.value).run()}
      />
      <select
        title={t('editor.toolbar.fontFamily')}
        className="border-border bg-background h-7 rounded border px-1 text-xs"
        value={state.fontFamily}
        onChange={(e) => {
          if (e.target.value) editor.chain().focus().setFontFamily(e.target.value).run();
          else editor.chain().focus().unsetFontFamily().run();
        }}
      >
        {FONT_FAMILIES.map((f) => (
          <option key={f.labelKey} value={f.value}>
            {t(f.labelKey)}
          </option>
        ))}
      </select>
      <select
        title={t('editor.toolbar.fontSize')}
        className="border-border bg-background h-7 rounded border px-1 text-xs"
        value={state.fontSize}
        onChange={(e) => {
          if (e.target.value) editor.chain().focus().setFontSize(e.target.value).run();
          else editor.chain().focus().unsetFontSize().run();
        }}
      >
        {FONT_SIZES.map((f) => (
          <option key={f.value} value={f.value}>
            {f.label ?? t('editor.toolbar.optionDefault')}
          </option>
        ))}
      </select>

      <div className="bg-border mx-1 h-5 w-px" />

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = '';
          if (file) onInsertImage?.(file);
        }}
      />
      <ToolbarButton
        title={t('editor.toolbar.insertImage')}
        disabled={isUploadingImage}
        onClick={() => fileInputRef.current?.click()}
      >
        <ImageIcon />
      </ToolbarButton>
      <ToolbarButton
        title={t('editor.toolbar.insertTable')}
        onClick={() =>
          editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
        }
      >
        <TableIcon />
      </ToolbarButton>

      {state.inTable && (
        <>
          <div className="bg-border mx-1 h-5 w-px" />
          <Button
            type="button"
            variant="ghost"
            size="xs"
            onClick={() => editor.chain().focus().addRowBefore().run()}
          >
            {t('editor.toolbar.addRowAbove')}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="xs"
            onClick={() => editor.chain().focus().addRowAfter().run()}
          >
            {t('editor.toolbar.addRowBelow')}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="xs"
            onClick={() => editor.chain().focus().deleteRow().run()}
          >
            {t('editor.toolbar.deleteRow')}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="xs"
            onClick={() => editor.chain().focus().addColumnBefore().run()}
          >
            {t('editor.toolbar.addColumnBefore')}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="xs"
            onClick={() => editor.chain().focus().addColumnAfter().run()}
          >
            {t('editor.toolbar.addColumnAfter')}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="xs"
            onClick={() => editor.chain().focus().deleteColumn().run()}
          >
            {t('editor.toolbar.deleteColumn')}
          </Button>
          <ToolbarButton
            title={t('editor.toolbar.deleteTable')}
            onClick={() => editor.chain().focus().deleteTable().run()}
          >
            <Trash2 />
          </ToolbarButton>
        </>
      )}

      <div className="ml-auto flex items-center gap-1">
        <ToolbarButton
          title={t('editor.toolbar.undo')}
          disabled={!state.canUndo}
          onClick={() => editor.chain().focus().undo().run()}
        >
          <Undo2 />
        </ToolbarButton>
        <ToolbarButton
          title={t('editor.toolbar.redo')}
          disabled={!state.canRedo}
          onClick={() => editor.chain().focus().redo().run()}
        >
          <Redo2 />
        </ToolbarButton>
      </div>
    </div>
  );
}

