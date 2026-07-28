import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import { renderWithProviders } from '@/test/render';
import { GenieConversationPage } from './GenieConversationPage';
import { createConversation, getConversation } from '@/api/conversations';
import { sendMessageStream } from '@/api/chat';
import type { ChatStreamHandlers } from '@/api/chat';
import type { ConversationDetailRead } from '@/api/types';

vi.mock('@/api/conversations');
vi.mock('@/api/chat');

const mockGetConversation = vi.mocked(getConversation);
const mockCreateConversation = vi.mocked(createConversation);
const mockSendMessageStream = vi.mocked(sendMessageStream);

const COMPOSER_PLACEHOLDER = 'Ask Genie about your diary…';

// jsdom doesn't implement scrollIntoView; the page calls it on every message-list update.
Element.prototype.scrollIntoView = vi.fn();

function renderAtRoute(route: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/genie/new" element={<GenieConversationPage />} />
      <Route path="/genie/:id" element={<GenieConversationPage />} />
    </Routes>,
    { route, withAuthProvider: false },
  );
}

function conversation(overrides: Partial<ConversationDetailRead> = {}): ConversationDetailRead {
  return {
    id: 'conv-1',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    preview: null,
    messages: [],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('GenieConversationPage', () => {
  it("renders an existing conversation's history with citations", async () => {
    mockGetConversation.mockResolvedValue(
      conversation({
        preview: 'What did I write yesterday?',
        messages: [
          {
            id: 'u1',
            role: 'user',
            content: 'What did I write yesterday?',
            created_at: '2026-01-01T00:00:00Z',
            citations: [],
          },
          {
            id: 'a1',
            role: 'assistant',
            content: 'You wrote about hiking.',
            created_at: '2026-01-01T00:00:01Z',
            citations: [{ diary_entry_id: 'd1', title: 'Hiking day', entry_date: '2026-01-01' }],
          },
        ],
      }),
    );

    renderAtRoute('/genie/conv-1');

    expect(await screen.findByText('What did I write yesterday?')).toBeInTheDocument();
    expect(await screen.findByText('You wrote about hiking.')).toBeInTheDocument();
    const citationLink = screen.getByRole('link', { name: 'Hiking day' });
    expect(citationLink).toHaveAttribute('href', '/diaries/d1');
  });

  it('streams a reply incrementally, then finalizes from the server', async () => {
    const user = userEvent.setup();
    mockGetConversation
      .mockResolvedValueOnce(conversation())
      .mockResolvedValueOnce(
        conversation({
          preview: 'hello',
          messages: [
            { id: 'u1', role: 'user', content: 'hello', created_at: '2026-01-01T00:00:00Z', citations: [] },
            {
              id: 'a1',
              role: 'assistant',
              content: 'Hello world',
              created_at: '2026-01-01T00:00:01Z',
              citations: [{ diary_entry_id: 'd1', title: 'Hiking day', entry_date: '2026-01-01' }],
            },
          ],
        }),
      );

    let resolveGate: () => void = () => {};
    const gate = new Promise<void>((resolve) => {
      resolveGate = resolve;
    });
    mockSendMessageStream.mockImplementation(
      async (_conversationId: string, _content: string, handlers: ChatStreamHandlers) => {
        handlers.onCitations?.({
          citations: [{ diary_entry_id: 'd1', title: 'Hiking day', entry_date: '2026-01-01' }],
        });
        handlers.onToken?.({ text: 'Hel' });
        await gate;
        handlers.onToken?.({ text: 'lo world' });
        handlers.onDone?.({ id: 'a1', created_at: '2026-01-01T00:00:01Z' });
      },
    );

    renderAtRoute('/genie/conv-1');

    const textarea = await screen.findByPlaceholderText(COMPOSER_PLACEHOLDER);
    await user.type(textarea, 'hello');
    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(await screen.findByText('hello')).toBeInTheDocument();
    expect(await screen.findByText('Hel')).toBeInTheDocument();
    expect(screen.getByText('▍')).toBeInTheDocument();

    resolveGate();

    expect(await screen.findByText('Hello world')).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'Hiking day' })).toBeInTheDocument();
    await waitFor(() => expect(mockGetConversation).toHaveBeenCalledTimes(2));
  });

  it("keeps the user's message visible and shows an error on generation failure", async () => {
    const user = userEvent.setup();
    mockGetConversation.mockResolvedValueOnce(conversation());
    mockSendMessageStream.mockImplementation(
      async (_conversationId: string, _content: string, handlers: ChatStreamHandlers) => {
        handlers.onError?.({ message: 'Something broke' });
      },
    );

    renderAtRoute('/genie/conv-1');

    const textarea = await screen.findByPlaceholderText(COMPOSER_PLACEHOLDER);
    await user.type(textarea, 'hello');
    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(await screen.findByText('hello')).toBeInTheDocument();
    expect(await screen.findByRole('alert')).toHaveTextContent('Something broke');
  });

  it('creates a conversation and sends the first message from /genie/new', async () => {
    const user = userEvent.setup();
    mockCreateConversation.mockResolvedValue({
      id: 'conv-2',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      preview: null,
    });
    mockGetConversation.mockResolvedValue(conversation({ id: 'conv-2' }));
    // Deliberately never calls onDone: this test only needs to prove the ref-guarded
    // new-conversation handoff (create -> navigate -> send) fires exactly once with the right
    // id/content; the "done -> refetch" behavior is already covered by the streaming test above,
    // and asserting it here too would race the still-in-flight initial /genie/:id fetch.
    mockSendMessageStream.mockImplementation(
      async (_conversationId: string, _content: string, handlers: ChatStreamHandlers) => {
        handlers.onToken?.({ text: 'Hello world' });
      },
    );

    renderAtRoute('/genie/new');

    const textarea = await screen.findByPlaceholderText(COMPOSER_PLACEHOLDER);
    await user.type(textarea, 'hello');
    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(await screen.findByText('hello')).toBeInTheDocument();
    await waitFor(() => expect(mockCreateConversation).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(mockSendMessageStream).toHaveBeenCalledWith('conv-2', 'hello', expect.anything()),
    );
  });
});
