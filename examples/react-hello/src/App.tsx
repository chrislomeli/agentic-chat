import { useState } from "react";
import { useChat, type ChatMessage } from "./useChat";

const roleColor: Record<ChatMessage["role"], string> = {
  user: "#0066cc",
  assistant: "#008000",
  system: "#aa6600",
};

export default function App() {
  const { messages, isLoading, error, send } = useChat();
  const [input, setInput] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    send(input);
    setInput("");
  };

  return (
    <div
      style={{
        maxWidth: 680,
        margin: "2rem auto",
        padding: "0 1rem",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <h1 style={{ marginBottom: 4 }}>agent_chat — hello world</h1>
      <p style={{ color: "#666", marginTop: 0 }}>
        Backend: <code>uv run uvicorn examples.hello_world:app</code> on :8000.
        Try a message, then one ending in <code>?</code>, then <code>/quit</code>.
      </p>

      <div
        style={{
          border: "1px solid #ddd",
          borderRadius: 8,
          padding: 12,
          minHeight: 260,
        }}
      >
        {messages.length === 0 && (
          <em style={{ color: "#999" }}>No messages yet.</em>
        )}
        {messages.map((m) => (
          <div key={m.id} style={{ margin: "8px 0" }}>
            <span style={{ fontWeight: 600, color: roleColor[m.role] }}>
              {m.role}:
            </span>{" "}
            <span style={{ whiteSpace: "pre-wrap" }}>{m.content}</span>
          </div>
        ))}
      </div>

      {error && <p style={{ color: "crimson" }}>Error: {error}</p>}

      <form onSubmit={submit} style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          disabled={isLoading}
          style={{ flex: 1, padding: 8 }}
        />
        <button type="submit" disabled={isLoading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
