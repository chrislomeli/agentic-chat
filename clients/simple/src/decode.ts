/**
 * decode.ts — turn an SSE byte stream into typed Frames.
 *
 * This is the front-end twin of agent_chat's transport.stream_turn: where the
 * Python side encodes Frames to SSE, this decodes SSE back into Frames. It is a
 * proper line-buffered SSE parser (handles event/data split across network
 * chunks and multi-line `data:` payloads), unlike a naive split-on-newline.
 */
import type { Frame, FrameKind } from "./frames.js";

const DATA_PREFIX = "data:";
const EVENT_PREFIX = "event:";

/**
 * Decode a Server-Sent-Events body into an async stream of {@link Frame}s.
 *
 * @param body   the `ReadableStream` from `fetch(...).body`
 * @example
 *   const res = await fetch(url);
 *   for await (const frame of decodeFrames(res.body!)) { ... }
 */
export async function* decodeFrames(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<Frame> {
  const reader = body.getReader();
  const decoder = new TextDecoder();

  let buffer = "";
  let eventName = "message";
  let dataLines: string[] = [];

  /** Assemble the buffered event lines into a Frame (or null if empty). */
  const flush = (): Frame | null => {
    if (dataLines.length === 0) {
      eventName = "message";
      return null;
    }
    const raw = dataLines.join("\n");
    const kind = eventName as FrameKind;
    dataLines = [];
    eventName = "message";

    let payload: Record<string, unknown> = {};
    try {
      payload = JSON.parse(raw) as Record<string, unknown>;
    } catch {
      payload = {};
    }
    return { kind, ...payload } as Frame;
  };

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let nl: number;
      while ((nl = buffer.indexOf("\n")) !== -1) {
        // Strip a trailing CR so CRLF streams parse the same as LF.
        const line = buffer.slice(0, nl).replace(/\r$/, "");
        buffer = buffer.slice(nl + 1);

        if (line === "") {
          const frame = flush(); // blank line = event boundary
          if (frame) yield frame;
        } else if (line.startsWith(EVENT_PREFIX)) {
          eventName = line.slice(EVENT_PREFIX.length).trim();
        } else if (line.startsWith(DATA_PREFIX)) {
          // SSE allows an optional single leading space after the colon.
          dataLines.push(line.slice(DATA_PREFIX.length).replace(/^ /, ""));
        }
        // Lines beginning with ":" are comments and are ignored.
      }
    }
    // Emit a final event if the stream ended without a trailing blank line.
    const frame = flush();
    if (frame) yield frame;
  } finally {
    reader.releaseLock();
  }
}
