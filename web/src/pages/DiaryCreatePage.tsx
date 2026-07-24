import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { DiaryEditor } from '@/components/editor/DiaryEditor';

const SAMPLE_IMAGE =
  'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCI+PHJlY3Qgd2lkdGg9IjYwIiBoZWlnaHQ9IjYwIiBmaWxsPSIjZjk3MzE2Ii8+PC9zdmc+';

// Temporary, section-7-only demo: exercises every editor extension via seeded markdown (proves
// the load direction) and a live raw-markdown preview (proves the save direction). Section 8
// replaces this with the real create form (title/date fields, validation, POST /diaries).
const SAMPLE_MARKDOWN = `# Diary editor smoke test

A paragraph with **bold**, *italic*, ~~strikethrough~~, and \`inline code\`, plus a [link](https://example.com).

<span style="color: #dc2626">Colored text</span> and <span style="font-family: ui-serif, Georgia, serif; font-size: 24px">serif, larger text</span>, in the same paragraph.

<p style="text-align: center">A centered paragraph.</p>

<h2 style="text-align: right">Right-aligned heading</h2>

## Lists

- Bullet one
- Bullet two

1. Ordered one
2. Ordered two

- [ ] Unchecked task
- [x] Checked task

> A blockquote.

\`\`\`js
console.log('code block');
\`\`\`

| Left | Center | Right |
| :--- | :---: | ---: |
| a | b | c |
| d | e | f |

---

![Sample image](${SAMPLE_IMAGE})
`;

export function DiaryCreatePage() {
  const { t } = useTranslation();
  const [markdown, setMarkdown] = useState(SAMPLE_MARKDOWN);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t('diary.createTitle')}</h1>
      <DiaryEditor content={markdown} onChange={setMarkdown} />
      <div>
        <p className="text-muted-foreground mb-1 text-xs">
          Live markdown output (section 7 verification only — removed once section 8 wires up the
          real create form):
        </p>
        <pre className="bg-muted overflow-x-auto rounded-md p-3 text-xs whitespace-pre-wrap">
          {markdown}
        </pre>
      </div>
    </div>
  );
}
