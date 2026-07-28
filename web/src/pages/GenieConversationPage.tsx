import { useCallback, useEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChatBubble } from '@/components/genie/ChatBubble';
import { createConversation, getConversation } from '@/api/conversations';
import { sendMessageStream } from '@/api/chat';
import { ApiError } from '@/api/errors';
import type { CitationRead, MessageRead } from '@/api/types';

function makeUserMessage(content: string): MessageRead {
  return {
    id: crypto.randomUUID(),
    role: 'user',
    content,
    created_at: new Date().toISOString(),
    citations: [],
  };
}

export function GenieConversationPage() {
  const { id } = useParams<{ id?: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  const [draft, setDraft] = useState('');
  const [localMessages, setLocalMessages] = useState<MessageRead[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamText, setStreamText] = useState('');
  const [streamCitations, setStreamCitations] = useState<CitationRead[]>([]);
  const [streamError, setStreamError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const pendingHandledRef = useRef(false);

  const conversationQuery = useQuery({
    queryKey: ['conversations', id],
    queryFn: () => getConversation(id!),
    enabled: !!id,
    retry: false,
  });

  const runSend = useCallback(
    async (conversationId: string, content: string) => {
      const userMessage = makeUserMessage(content);
      setLocalMessages((prev) => [...prev, userMessage]);
      setIsStreaming(true);
      setStreamError(null);
      setStreamText('');
      setStreamCitations([]);

      let accumulatedText = '';
      let citations: CitationRead[] = [];
      let settled = false;

      try {
        await sendMessageStream(conversationId, content, {
          onCitations: (event) => {
            citations = event.citations;
            setStreamCitations(event.citations);
          },
          onToken: (event) => {
            accumulatedText += event.text;
            setStreamText(accumulatedText);
          },
          onDone: (event) => {
            settled = true;
            // Re-fetch rather than hand-append the just-streamed turn: the backend already
            // persists the user message before generation starts (and the assistant message
            // before this "done" event), so a real (slow) reply gives plenty of time for some
            // other refetch (e.g. refetchOnWindowFocus) to already have pulled this turn into
            // the cache. Appending on top of that would double it up; re-fetching and taking the
            // server's list wholesale can't.
            void queryClient
              .fetchQuery({
                queryKey: ['conversations', conversationId],
                queryFn: () => getConversation(conversationId),
              })
              .then(() => {
                setLocalMessages((prev) => prev.filter((message) => message.id !== userMessage.id));
              })
              .catch(() => {
                const assistantMessage: MessageRead = {
                  id: event.id,
                  role: 'assistant',
                  content: accumulatedText,
                  created_at: event.created_at,
                  citations,
                };
                setLocalMessages((prev) => [...prev, assistantMessage]);
              })
              .finally(() => {
                setIsStreaming(false);
                setStreamText('');
                setStreamCitations([]);
              });
            void queryClient.invalidateQueries({ queryKey: ['conversations'], exact: true });
          },
          onError: (event) => {
            settled = true;
            setStreamError(event.message);
            setIsStreaming(false);
          },
        });
        // The connection can close (server crash, proxy timeout, network drop) without ever
        // sending a "done" or "error" event — don't leave the UI stuck showing "streaming"
        // forever in that case.
        if (!settled) {
          setStreamError(t('common.genericError'));
          setIsStreaming(false);
        }
      } catch {
        setStreamError(t('common.genericError'));
        setIsStreaming(false);
      }
    },
    [queryClient, t],
  );

  // Resumes streaming after the /genie/new -> /genie/:id navigation, regardless of whether that
  // navigation remounted this page (see plan doc for why this can't just live in handleSend).
  useEffect(() => {
    const pendingMessage = (location.state as { pendingMessage?: string } | null)?.pendingMessage;
    if (!id || !pendingMessage || pendingHandledRef.current) return;
    pendingHandledRef.current = true;

    void runSend(id, pendingMessage);
    void navigate(location.pathname, { replace: true, state: null });
  }, [id, location.state, location.pathname, navigate, runSend]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversationQuery.data?.messages.length, localMessages.length, streamText]);

  async function handleSend() {
    const content = draft.trim();
    if (!content || isStreaming) return;
    setDraft('');
    setStreamError(null);

    if (!id) {
      setIsStreaming(true);
      try {
        const conversation = await createConversation();
        void navigate(`/genie/${conversation.id}`, {
          replace: true,
          state: { pendingMessage: content },
        });
      } catch {
        setStreamError(t('common.genericError'));
        setIsStreaming(false);
      }
      return;
    }

    void runSend(id, content);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  }

  const isNotFound =
    !!id && conversationQuery.error instanceof ApiError && conversationQuery.error.status === 404;
  const isLoadError = !!id && !!conversationQuery.error && !isNotFound;

  if (id && conversationQuery.isLoading) {
    return <p className="text-muted-foreground text-sm">{t('common.loading')}</p>;
  }

  if (isNotFound) {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-muted-foreground text-sm">{t('genie.conversationNotFound')}</p>
        <Link to="/genie" className="text-primary text-sm underline underline-offset-4">
          {t('genie.backToList')}
        </Link>
      </div>
    );
  }

  if (isLoadError) {
    return <p className="text-destructive text-sm">{t('common.genericError')}</p>;
  }

  const allMessages = [...(conversationQuery.data?.messages ?? []), ...localMessages];

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col gap-3">
      <Link to="/genie" className="text-primary self-start text-sm underline underline-offset-4">
        {t('genie.backToList')}
      </Link>

      <ScrollArea className="flex-1 rounded-md border p-4">
        <div className="flex flex-col gap-3">
          {allMessages.map((message) => (
            <ChatBubble
              key={message.id}
              role={message.role}
              content={message.content}
              citations={message.citations}
            />
          ))}
          {isStreaming && (
            <ChatBubble role="assistant" content={streamText} citations={streamCitations} streaming />
          )}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {isStreaming && !streamText && (
        <p className="text-muted-foreground text-sm">{t('genie.streamingIndicator')}</p>
      )}
      {streamError && (
        <p role="alert" className="text-destructive text-sm">
          {streamError}
        </p>
      )}

      <div className="flex gap-2">
        <Textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('genie.composerPlaceholder')}
          disabled={isStreaming}
          className="flex-1"
        />
        <Button onClick={() => void handleSend()} disabled={isStreaming || !draft.trim()}>
          {t('genie.sendButton')}
        </Button>
      </div>
    </div>
  );
}
