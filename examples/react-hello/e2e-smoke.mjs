// Drive the live hello_world backend with the BUILT agent-chat-client.
// Proves the SSE decoder + ChatClient work end to end against real frames.
import { ChatClient } from "../../clients/typescript/dist/index.js";

const client = new ChatClient("http://localhost:8000");

async function turn(sid, message) {
  console.log(`\n--- turn: ${JSON.stringify(message)} ---`);
  for await (const frame of client.sendMessage(sid, message)) {
    console.log(frame.kind, JSON.stringify({ ...frame, kind: undefined }));
  }
}

const sid = await client.createSession();
console.log("session:", sid);
await turn(sid, "hello there"); // tool_call + tokens + ask_human (no '?')
await turn(sid, "all good?"); // tool_call + tokens + state_update ('?')
await turn(sid, "/quit"); // terminate
await client.endSession(sid);
console.log("\nOK");
