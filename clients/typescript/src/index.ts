/**
 * agent-chat-client — framework-agnostic TypeScript client for agent_chat.
 *
 * Two layers, mirroring the Python package:
 *   decodeFrames — the SSE → Frame decoder (the transport twin)
 *   ChatClient   — a thin fetch client over /sessions and /chat/{id}
 *
 * Bring your own UI: feed the Frames to a React hook, a Svelte store, or a
 * plain loop. See examples/react-hello for a reference React integration.
 */
export { decodeFrames } from "./decode.js";
export { ChatClient } from "./client.js";
export type { SendOptions } from "./client.js";
export {
  TERMINAL_KINDS,
  type Frame,
  type FrameKind,
  type TokenFrame,
  type ToolCallFrame,
  type SubgraphFrame,
  type AskHumanFrame,
  type StateUpdateFrame,
  type TerminateFrame,
  type DoneFrame,
  type ErrorFrame,
} from "./frames.js";
