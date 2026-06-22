# agent-chat-client

Framework-agnostic **TypeScript client** for the [`agent_chat`](../../README.md)
Action protocol. The front-end twin of the Python backend: where the server
encodes Frames to SSE, this decodes SSE back into typed Frames.

Two layers, mirroring the Python package:

| Layer | What it is |
|---|---|
| `decodeFrames(body)` | a robust, line-buffered SSE → `Frame` decoder |
| `ChatClient(baseUrl)` | a thin `fetch` client over `/sessions` and `/chat/{id}` |

Bring your own UI — feed the Frames to a React hook, a Svelte store, or a plain
loop. See [`examples/react-hello`](../../examples/react-hello) for a reference
React integration.

## Use it

```ts
import { ChatClient } from "agent-chat-client";

const client = new ChatClient("/api");
const sid = await client.createSession();

for await (const frame of client.sendMessage(sid, "hello")) {
  switch (frame.kind) {
    case "token":        appendText(frame.text); break;   // streamed AI text
    case "ask_human":    showPrompt(frame.prompt); break;  // turn ended; reply next
    case "state_update": notify(frame.message); break;     // durable state changed
    case "tool_call":    /* frame.name, frame.args */ break;
    case "terminate":    await client.endSession(sid); break;
    case "error":        showError(frame.message); break;
    case "done":         break;                            // terminal, always last
  }
}
```

`Frame` is a discriminated union on `kind`, so the `switch` narrows each
payload. The stream always ends with a `done` (success) or `error` frame — the
transport appends it, so you never wait forever.

## Just the decoder

If you already have a `Response` (your own fetch, auth headers, etc.):

```ts
import { decodeFrames } from "agent-chat-client";

const res = await fetch("/api/chat/" + sid, { method: "POST", body });
for await (const frame of decodeFrames(res.body!)) { /* ... */ }
```

## Install in a real project

```bash
# from a private git remote (pin to a tag):
npm install "agent-chat-client@github:you/agent-chat#v0.1.0"   # if published from this subdir
# or a local path while co-developing:
npm install ../agent_chat/clients/typescript
```

The import path (`agent-chat-client`) stays identical to the example, which
aliases the source directly for zero-build local dev.

## Build

```bash
npm install
npm run build   # tsc -> dist/ (ESM + .d.ts)
```
