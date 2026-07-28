import { afterEach, describe, expect, it, vi } from 'vitest';
import { sendMessageStream } from './chat';
import { ApiError } from './errors';
import type { ChatStreamHandlers } from './chat';

function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let i = 0;
  return new ReadableStream({
    pull(controller) {
      if (i < chunks.length) {
        controller.enqueue(encoder.encode(chunks[i++]));
      } else {
        controller.close();
      }
    },
  });
}

function stubFetchWithStream(chunks: string[], init: ResponseInit = { status: 200 }) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response(makeStream(chunks), init)),
  );
}

function collectHandlers() {
  const onCitations = vi.fn();
  const onToken = vi.fn();
  const onDone = vi.fn();
  const onError = vi.fn();
  const handlers: ChatStreamHandlers = { onCitations, onToken, onDone, onError };
  return { handlers, onCitations, onToken, onDone, onError };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('sendMessageStream', () => {
  it('dispatches citations, then tokens, then done in order', async () => {
    stubFetchWithStream([
      'event: citations\ndata: {"citations":[{"diary_entry_id":"1","title":"A","entry_date":"2026-01-01"}]}\n\n',
      'event: token\ndata: {"text":"Hello "}\n\n',
      'event: token\ndata: {"text":"world"}\n\n',
      'event: done\ndata: {"id":"msg-1","created_at":"2026-01-01T00:00:00Z"}\n\n',
    ]);
    const { handlers, onCitations, onToken, onDone, onError } = collectHandlers();

    await sendMessageStream('conv-1', 'hi', handlers);

    expect(onCitations).toHaveBeenCalledWith({
      citations: [{ diary_entry_id: '1', title: 'A', entry_date: '2026-01-01' }],
    });
    expect(onToken).toHaveBeenNthCalledWith(1, { text: 'Hello ' });
    expect(onToken).toHaveBeenNthCalledWith(2, { text: 'world' });
    expect(onDone).toHaveBeenCalledWith({ id: 'msg-1', created_at: '2026-01-01T00:00:00Z' });
    expect(onError).not.toHaveBeenCalled();

    const callOrder = [
      ...onCitations.mock.invocationCallOrder,
      ...onToken.mock.invocationCallOrder,
      ...onDone.mock.invocationCallOrder,
    ];
    expect(callOrder).toEqual([...callOrder].sort((a, b) => a - b));
  });

  it('parses a frame whose data line is split across two reads', async () => {
    stubFetchWithStream(['event: token\ndata: {"te', 'xt":"hello"}\n\n']);
    const { handlers, onToken } = collectHandlers();

    await sendMessageStream('conv-1', 'hi', handlers);

    expect(onToken).toHaveBeenCalledTimes(1);
    expect(onToken).toHaveBeenCalledWith({ text: 'hello' });
  });

  it('parses CRLF-separated blocks the same as LF', async () => {
    stubFetchWithStream(['event: token\r\ndata: {"text":"hi"}\r\n\r\n']);
    const { handlers, onToken } = collectHandlers();

    await sendMessageStream('conv-1', 'hi', handlers);

    expect(onToken).toHaveBeenCalledWith({ text: 'hi' });
  });

  it('rejects with an ApiError and calls no handlers on a non-OK response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'bad request' }), {
          status: 400,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    );
    const { handlers, onCitations, onToken, onDone, onError } = collectHandlers();

    await expect(sendMessageStream('conv-1', 'hi', handlers)).rejects.toMatchObject({
      status: 400,
      detail: 'bad request',
    } satisfies Partial<ApiError>);
    expect(onCitations).not.toHaveBeenCalled();
    expect(onToken).not.toHaveBeenCalled();
    expect(onDone).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });

  it('calls onError with a generic message when the response has no body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 200 })));
    const { handlers, onError } = collectHandlers();

    await sendMessageStream('conv-1', 'hi', handlers);

    expect(onError).toHaveBeenCalledWith({ message: expect.any(String) });
  });

  it('dispatches an error event mid-stream to onError instead of onDone', async () => {
    stubFetchWithStream([
      'event: token\ndata: {"text":"partial"}\n\n',
      'event: error\ndata: {"message":"generation failed"}\n\n',
    ]);
    const { handlers, onDone, onError } = collectHandlers();

    await sendMessageStream('conv-1', 'hi', handlers);

    expect(onError).toHaveBeenCalledWith({ message: 'generation failed' });
    expect(onDone).not.toHaveBeenCalled();
  });
});
