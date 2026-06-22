import { Chat } from 'agent-chat-react'

// The whole app is one drop-in component from the React client. Branding is
// props; the SSE/Frame plumbing lives in agent-chat-react → agent-chat-client.
export default function App() {
  return (
    <Chat
      title="Journal Agent"
      assistantName="Journal Agent"
      emptyIcon="📓"
      emptyText="Start a conversation with your journal agent. Type a message below."
    />
  )
}
