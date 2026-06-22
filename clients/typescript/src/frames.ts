/**
 * frames.ts — the TypeScript mirror of the agent_chat Action protocol.
 *
 * These types match the Python `Frame` subclasses in agent_chat/actions.py
 * one-for-one. On the wire each frame is an SSE event:
 *
 *     event: <kind>\n
 *     data:  <json payload>\n
 *     \n
 *
 * `kind` is the discriminator, so a `switch (frame.kind)` narrows the payload.
 */

export type FrameKind =
  | "token"
  | "tool_call"
  | "subgraph"
  | "ask_human"
  | "state_update"
  | "terminate"
  | "done"
  | "error";

/** One chunk of streamed model text. */
export interface TokenFrame {
  kind: "token";
  text: string;
}

/** The agent invoked a tool (notification). */
export interface ToolCallFrame {
  kind: "tool_call";
  name: string;
  args: Record<string, unknown>;
  result: unknown | null;
}

/** The agent delegated to a subgraph (notification). */
export interface SubgraphFrame {
  kind: "subgraph";
  name: string;
  status: "started" | "finished";
  detail: string | null;
}

/** The agent needs input; the turn ends here (no interrupt/resume). */
export interface AskHumanFrame {
  kind: "ask_human";
  prompt: string;
  field: string | null;
}

/** Durable state changed during the turn (observational notification). */
export interface StateUpdateFrame {
  kind: "state_update";
  message: string;
  patch: Record<string, unknown> | null;
}

/** The session is over. */
export interface TerminateFrame {
  kind: "terminate";
  reason: string | null;
}

/** Turn complete — terminal frame, always last on success. */
export interface DoneFrame {
  kind: "done";
}

/** The turn failed — terminal frame. */
export interface ErrorFrame {
  kind: "error";
  message: string;
}

/** Every frame that can cross the wire. */
export type Frame =
  | TokenFrame
  | ToolCallFrame
  | SubgraphFrame
  | AskHumanFrame
  | StateUpdateFrame
  | TerminateFrame
  | DoneFrame
  | ErrorFrame;

/** The two terminal kinds the transport appends to every turn. */
export const TERMINAL_KINDS: ReadonlySet<FrameKind> = new Set<FrameKind>([
  "done",
  "error",
]);
