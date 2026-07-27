import type {
  ChatCitationsEvent,
  ChatDoneEvent,
  ChatErrorEvent,
  ChatTokenEvent,
  SendMessageRequest,
} from './types';
import { API_URL } from './client';
import { ApiError } from './errors';

export interface ChatStreamHandlers {
  onCitations?: (event: ChatCitationsEvent) => void;
  onToken?: (event: ChatTokenEvent) => void;
  onDone?: (event: ChatDoneEvent) => void;
  onError?: (event: ChatErrorEvent) => void;
}

const GENERIC_ERROR_MESSAGE = 'Something went wrong generating a reply.';

export async function sendMessageStream(
  conversationId: string,
  content: string,
  handlers: ChatStreamHandlers,
): Promise<void> {
  const res = await fetch(`${API_URL}/conversations/${conversationId}/messages`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({ content } satisfies SendMessageRequest),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => undefined);
    throw new ApiError(res.status, body?.detail ?? res.statusText);
  }

  if (!res.body) {
    handlers.onError?.({ message: GENERIC_ERROR_MESSAGE });
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      let separatorIndex: number;
      while ((separatorIndex = buffer.indexOf('\n\n')) !== -1) {
        dispatchBlock(buffer.slice(0, separatorIndex), handlers);
        buffer = buffer.slice(separatorIndex + 2);
      }
    }
  } catch {
    handlers.onError?.({ message: GENERIC_ERROR_MESSAGE });
  } finally {
    reader.releaseLock();
  }
}

function dispatchBlock(rawBlock: string, handlers: ChatStreamHandlers): void {
  let eventName = '';
  let dataLine = '';
  for (const line of rawBlock.split('\n')) {
    if (line.startsWith('event:')) eventName = line.slice('event:'.length).trim();
    else if (line.startsWith('data:')) dataLine = line.slice('data:'.length).trim();
  }
  if (!eventName || !dataLine) return;

  const payload = JSON.parse(dataLine);
  switch (eventName) {
    case 'citations':
      handlers.onCitations?.(payload as ChatCitationsEvent);
      break;
    case 'token':
      handlers.onToken?.(payload as ChatTokenEvent);
      break;
    case 'done':
      handlers.onDone?.(payload as ChatDoneEvent);
      break;
    case 'error':
      handlers.onError?.(payload as ChatErrorEvent);
      break;
  }
}
