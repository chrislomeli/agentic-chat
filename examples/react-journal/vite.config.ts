import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

// Resolve sibling paths in the agent_chat repo relative to this config file.
const reactClientSrc = fileURLToPath(
  new URL('../../clients/react/src/index.ts', import.meta.url),
)
const coreClientSrc = fileURLToPath(
  new URL('../../clients/simple/src/index.ts', import.meta.url),
)
const repoRoot = fileURLToPath(new URL('../..', import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Consume both clients straight from source — no build step for local dev.
    // In a real project you'd `npm install agent-chat-react` and drop these
    // aliases; the import paths stay identical. The core alias is still needed
    // because agent-chat-react imports agent-chat-client internally.
    alias: {
      'agent-chat-react': reactClientSrc,
      'agent-chat-client': coreClientSrc,
    },
    // The react client is consumed from source, so dedupe React to a single
    // copy (the example's) — two React instances break hooks.
    dedupe: ['react', 'react-dom'],
  },
  server: {
    // Distinct port from react-hello (5173) so both can run side by side.
    port: 5174,
    strictPort: true,
    // The client source lives outside this app's root, so allow Vite to read it.
    fs: { allow: [repoRoot] },
    proxy: {
      // Forward /api to the hello_world FastAPI backend during development.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
