import { marked } from 'marked';
import DOMPurify from 'dompurify';

export function renderMarkdown(text: string): string {
  return DOMPurify.sanitize(marked.parse(text, { async: false }));
}
