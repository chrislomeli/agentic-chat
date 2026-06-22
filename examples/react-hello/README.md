# react-hello

A minimal React + Vite front end for the `agent_chat` hello-world backend. It
talks to the server **only** through [`agent-chat-client`](../../clients/typescript)
— `src/useChat.ts` is the reusable integration pattern; copy it into a real
project unchanged.

## Run the full stack

Two terminals, from the repo root:

```bash
# 1. backend (FastAPI, port 8000)
uv run uvicorn examples.hello_world:app --reload

# 2. front end (Vite dev server)
cd examples/react-hello
npm install
npm run dev        # open the printed http://localhost:5173
```

Vite proxies `/api` → `localhost:8000`, so the browser talks same-origin.
Try a normal message, then one ending in `?` (stops the `ask_human` loop and
emits a `state_update`), then `/quit` (ends the session).

## How the wiring works

- `src/useChat.ts` — a generic React hook over `ChatClient`. The only protocol
  logic is the `switch (frame.kind)`; everything else is React state.
- `vite.config.ts` — aliases `agent-chat-client` to the client's TypeScript
  source for zero-build local dev. In a real project you'd `npm install
  agent-chat-client` and drop the alias; the import path is identical.

## Headless smoke test

`e2e-smoke.mjs` drives the live backend with the built client (no browser).
Build the client first, then run it with the backend up:

```bash
(cd ../../clients/typescript && npm install && npm run build)
node e2e-smoke.mjs
```
