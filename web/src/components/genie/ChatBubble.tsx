import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { renderMarkdown } from '@/lib/markdown';
import type { CitationRead } from '@/api/types';

interface ChatBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  citations?: CitationRead[];
  streaming?: boolean;
}

export function ChatBubble({ role, content, citations = [], streaming = false }: ChatBubbleProps) {
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
        {citations.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            <span className="text-muted-foreground w-full text-xs">{t('genie.citationsLabel')}</span>
            {citations.map((citation) => (
              <Link
                key={citation.diary_entry_id}
                to={`/diaries/${citation.diary_entry_id}`}
                className="hover:bg-accent rounded-full border px-2 py-0.5 text-xs"
                target="_blank"
              >
                {citation.title ?? t('genie.citationDeleted')}
              </Link>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
