import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router';

import { Button } from '@/components/ui/button';
import { DeleteConversationDialog } from '@/components/genie/DeleteConversationDialog';
import { listConversations } from '@/api/conversations';
import { formatRelativeTime } from '@/lib/date';

export function GenieListPage() {
  const { t, i18n } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['conversations'],
    queryFn: listConversations,
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t('genie.listTitle')}</h1>
        <Button render={<Link to="/genie/new" />} nativeButton={false}>
          {t('genie.newChatButton')}
        </Button>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">{t('common.loading')}</p>}
      {isError && <p className="text-destructive text-sm">{t('common.genericError')}</p>}

      {data && data.length === 0 && (
        <p className="text-muted-foreground text-sm">{t('genie.emptyState')}</p>
      )}

      {data && data.length > 0 && (
        <ul className="divide-border border-border divide-y rounded-md border">
          {data.map((conversation) => (
            <li key={conversation.id} className="flex items-center">
              <Link
                to={`/genie/${conversation.id}`}
                className="hover:bg-muted flex flex-1 items-center justify-between p-3"
              >
                <span className="font-medium">{conversation.preview ?? t('genie.noPreview')}</span>
                <span className="text-muted-foreground ml-4 shrink-0 text-sm">
                  {formatRelativeTime(conversation.updated_at, i18n.resolvedLanguage)}
                </span>
              </Link>
              <div className="mr-3">
                <DeleteConversationDialog
                  conversationId={conversation.id}
                  conversationPreview={conversation.preview}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
