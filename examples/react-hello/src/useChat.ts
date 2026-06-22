/**
 * useChat.ts — a generic React hook over agent-chat-client.
 *
 * This is the reusable integration pattern: the hook knows the Frame protocol
 * (via the client) but nothing about any specific agent. Copy it into a real
 * project and it works against any agent_chat backend. The only protocol logic
 * is the `switch (frame.kind)` below — everything else is React state plumbing.
 */
import { useCallback, useRef, useState } from "react";
import { ChatClient, type Frame } from "agent-chat-client";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
}

const client = new ChatClient("/api");
const newId = () => Math.random().toString(36).slice(2, 11);

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const send = useCallback(
    async (text: string) => {
      const content = text.trim();
      if (!content || isLoading) return;

      setError(null);
      setIsLoading(true);
      setMessages((prev) => [...prev, { id: newId(), role: "user", content }]);

      // Placeholder bubble that streamed tokens append into.
      const assistantId = newId();
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "assistant", content: "" },
      ]);

      const pushSystem = (t: string) =>
        setMessages((prev) => [
          ...prev,
          { id: newId(), role: "system", content: t },
        ]);

      try {
        if (!sessionRef.current) {
          sessionRef.current = await client.createSession();
        }
        const sid = sessionRef.current;
        abortRef.current = new AbortController();

        let terminated = false;

        for await (const frame of client.sendMessage(sid, content, {
          signal: abortRef.current.signal,
        })) {
          switch (frame.kind) {
            case "token":
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + frame.text }
                    : m,
                ),
              );
              break;
            case "state_update":
              pushSystem(frame.message);
              break;
            case "ask_human":
              pushSystem(frame.prompt);
              break;
            case "tool_call":
              pushSystem(`[tool] ${frame.name}(${JSON.stringify(frame.args)})`);
              break;
            case "subgraph":
              pushSystem(`[subgraph] ${frame.name} ${frame.status}`);
              break;
            case "terminate":
              terminated = true;
              if (frame.reason) pushSystem(frame.reason);
              break;
            case "error":
              setError(frame.message);
              break;
            case "done":
              break;
          }
        }

        // Drop the placeholder if the turn produced no assistant text
        // (e.g. /quit, which only yields a terminate frame).
        setMessages((prev) =>
          prev.filter((m) => !(m.id === assistantId && m.content === "")),
        );

        if (terminated) {
          await client.endSession(sid);
          sessionRef.current = null;
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setError((err as Error).message ?? "Something went wrong");
        setMessages((prev) => prev.filter((m) => m.id !== assistantId));
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading],
  );

  return { messages, isLoading, error, send, stop };
}

export type { Frame };
