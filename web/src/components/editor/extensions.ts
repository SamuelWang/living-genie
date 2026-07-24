import type { JSONContent, MarkdownRendererHelpers, RenderContext } from '@tiptap/core';
import { Heading } from '@tiptap/extension-heading';
import { Paragraph } from '@tiptap/extension-paragraph';
import { TextStyle } from '@tiptap/extension-text-style';

/**
 * `color`/`fontFamily`/`fontSize`/`backgroundColor` (added to the `textStyle` mark by
 * @tiptap/extension-text-style's Color/FontFamily/FontSize/BackgroundColor) and `textAlign`
 * (added to paragraph/heading by @tiptap/extension-text-align) have no markdown syntax and no
 * built-in markdown render hook, so the markdown serializer would otherwise silently drop them.
 * Per architecture.md, they're represented as inline HTML (still valid CommonMark) instead.
 */
function inlineStyleFromAttrs(attrs: JSONContent['attrs']): string {
  if (!attrs) return '';
  const parts: string[] = [];
  if (attrs.color) parts.push(`color: ${attrs.color}`);
  if (attrs.fontFamily) parts.push(`font-family: ${attrs.fontFamily}`);
  if (attrs.fontSize) parts.push(`font-size: ${attrs.fontSize}`);
  if (attrs.backgroundColor) parts.push(`background-color: ${attrs.backgroundColor}`);
  return parts.join('; ');
}

export const StyledTextStyle = TextStyle.extend({
  renderMarkdown(node: JSONContent, h: MarkdownRendererHelpers) {
    const rendered = h.renderChildren(node);
    const style = inlineStyleFromAttrs(node.attrs);
    return style ? `<span style="${style}">${rendered}</span>` : rendered;
  },
});

// Tiptap's config types don't model `this.parent` for markdown hooks (unlike the other
// lifecycle methods), even though the runtime injects it the same way — see
// @tiptap/core's `getExtensionField`. The `any` cast below is required to reach the base
// implementation; it's the same value the built-in lifecycle methods get, just untyped here.
type MarkdownRenderer = (
  node: JSONContent,
  helpers: MarkdownRendererHelpers,
  ctx: RenderContext,
) => string;

export const AlignedParagraph = Paragraph.extend({
  renderMarkdown(node: JSONContent, h: MarkdownRendererHelpers, ctx: RenderContext) {
    const parent = (this as unknown as { parent: MarkdownRenderer }).parent;
    const rendered = parent(node, h, ctx);
    const align = node.attrs?.textAlign;
    if (!align || align === 'left' || !rendered) return rendered;
    return `<p style="text-align: ${align}">${rendered}</p>`;
  },
});

export const AlignedHeading = Heading.extend({
  renderMarkdown(node: JSONContent, h: MarkdownRendererHelpers, ctx: RenderContext) {
    const align = node.attrs?.textAlign;
    if (!align || align === 'left') {
      const parent = (this as unknown as { parent: MarkdownRenderer }).parent;
      return parent(node, h, ctx);
    }
    const level = typeof node.attrs?.level === 'number' ? node.attrs.level : 1;
    const rendered = node.content ? h.renderChildren(node.content) : '';
    return `<h${level} style="text-align: ${align}">${rendered}</h${level}>`;
  },
});
