# react-journal

A **fuller, styled** React + Vite front end for the `agent_chat` hello-world
backend — the polished sibling of [`react-hello`](../react-hello). It
demonstrates the **batteries-included** path: the entire app is the drop-in
`<Chat>` component from [`agent-chat-react`](../../clients/react), branded with
props (`src/App.tsx` is ~10 lines).

| | `react-hello` | `react-journal` (this) |
|---|---|---|
| Consumes | `useChat` hook only | the `<Chat>` component |
| Styling | none (inline) | Tailwind + Google Fonts (from the client) |
| Use it for | the minimal headless integration | a closer-to-production drop-in UI |

Both consume the same `agent-chat-react` client over the identical `Frame`
protocol — only how much of the client they use differs.

## Run the full stack

Two terminals, from the repo root:

```bash
# 1. backend (FastAPI, port 8000)
uv run uvicorn examples.hello_world:app --reload

# 2. front end (Vite dev server)
cd examples/react-journal
npm install
npm run dev        # → http://localhost:5174
```

Vite proxies `/api` → `localhost:8000`, so the browser talks same-origin.
Try a normal message, then one ending in `?` (drives the `ask_human` loop and
emits a `state_update`), then `/quit` (ends the session).

> This example runs on **5174**; [`react-hello`](../react-hello) runs on
> **5173**, so both can be up at once against the one shared `:8000` backend.

## How the wiring works

- `src/App.tsx` — renders `<Chat title="Journal Agent" … />`. The hook,
  streaming, Frame handling, and styled components all live in
  `agent-chat-react`; the app only supplies branding.
- `tailwind.config.js` — its `content` globs include the client's source
  (`../../clients/react/src`) so the component classes aren't purged.
- `vite.config.ts` — aliases `agent-chat-react` (and the `agent-chat-client` it
  depends on) to source for zero-build local dev, and dedupes React to a single
  copy. In a real project you'd `npm install agent-chat-react` and drop the
  aliases; the import path is identical.
