import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { renderMarkdown } from '@/lib/markdown';
import type { MessageReference } from '@/api/types';

interface ChatBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  references?: MessageReference[];
  streaming?: boolean;
}

function referenceHref(reference: MessageReference): string {
  return reference.source_type === 'todo' ? `/todos/${reference.id}` : `/diaries/${reference.id}`;
}

export function ChatBubble({ role, content, references = [], streaming = false }: ChatBubbleProps) {
  const { t } = useTranslation();
  const isUser = role === 'user';

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <Card
        className={cn(
          'max-w-[80%] p-3 text-sm',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted',
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{content}</p>
        ) : (
          <div
            className="prose prose-sm max-w-none [&_p]:my-1 first:[&_p]:mt-0 last:[&_p]:mb-0"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
          />
        )}
        {streaming && <span className="animate-pulse">▍</span>}
        {references.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            <span className="text-muted-foreground w-full text-xs">{t('genie.referencesLabel')}</span>
            {references.map((reference) => (
              <Link
                key={reference.id}
                to={referenceHref(reference)}
                className="hover:bg-accent rounded-full border px-2 py-0.5 text-xs"
                target="_blank"
              >
                {reference.title ?? t('genie.referenceDeleted')}
                {reference.source_type === 'todo' && reference.completed && ' ✓'}
              </Link>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
