import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// Resolve sibling paths in the agent_chat repo relative to this config file.
const clientSrc = fileURLToPath(
  new URL("../../clients/typescript/src/index.ts", import.meta.url),
);
const repoRoot = fileURLToPath(new URL("../..", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Consume the TypeScript client straight from source — no build step
    // needed for local dev. In a real project you'd `npm install agent-chat-client`
    // and drop this alias; the import path stays identical.
    alias: {
      "agent-chat-client": clientSrc,
    },
  },
  server: {
    // The client source lives outside this app's root, so allow Vite to read it.
    fs: { allow: [repoRoot] },
    proxy: {
      // Forward /api to the hello_world FastAPI backend during development.
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
