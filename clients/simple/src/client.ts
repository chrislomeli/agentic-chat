/**
 * client.ts — a thin fetch client over the agent_chat HTTP surface.
 *
 * Wraps the three endpoints create_chat_app exposes and yields typed Frames for
 * a turn. It is framework-agnostic: a React hook, Svelte store, or plain script
 * can drive it. The only domain assumption is the agent_chat endpoint shape.
 */
import { decodeFrames } from "./decode.js";
import type { Frame } from "./frames.js";

export interface SendOptions {
  /** Abort the in-flight turn (e.g. a "stop" button). */
  signal?: AbortSignal;
  /** Extra per-turn metadata forwarded to the runner's TurnRequest. */
  metadata?: Record<string, unknown>;
}

/**
 * Client for an agent_chat backend.
 *
 * @example
 *   const client = new ChatClient("/api");
 *   const sid = await client.createSession();
 *   for await (const frame of client.sendMessage(sid, "hi")) {
 *     if (frame.kind === "token") process.stdout.write(frame.text);
 *   }
 */
export class ChatClient {
  /** @param baseUrl base path the endpoints live under (default "/api"). */
  constructor(private readonly baseUrl: string = "/api") {}

  /** POST /sessions — allocate a server-side session id. */
  async createSession(): Promise<string> {
    const res = await fetch(`${this.baseUrl}/sessions`, { method: "POST" });
    if (!res.ok) throw new Error(`createSession failed: HTTP ${res.status}`);
    const data = (await res.json()) as { session_id: string };
    return data.session_id;
  }

  /**
   * POST /chat/{sessionId} — run one turn, yielding Frames as they stream.
   * The stream always ends with a `done` or `error` frame (appended by the
   * transport), so consumers can stop on either.
   */
  async *sendMessage(
    sessionId: string,
    message: string,
    options: SendOptions = {},
  ): AsyncGenerator<Frame> {
    const res = await fetch(`${this.baseUrl}/chat/${sessionId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: options.signal,
      body: JSON.stringify({ message, metadata: options.metadata ?? {} }),
    });
    if (!res.ok) throw new Error(`chat failed: HTTP ${res.status}`);
    if (!res.body) throw new Error("chat response has no body to stream");
    yield* decodeFrames(res.body);
  }

  /** DELETE /sessions/{sessionId} — end the session (best-effort). */
  async endSession(sessionId: string): Promise<void> {
    try {
      await fetch(`${this.baseUrl}/sessions/${sessionId}`, {
        method: "DELETE",
      });
    } catch {
      // best-effort cleanup; don't surface to the UI
    }
  }
}
