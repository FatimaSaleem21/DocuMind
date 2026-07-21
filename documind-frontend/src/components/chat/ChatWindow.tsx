import { useChat } from "../../hooks/useChat";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";

export function ChatWindow() {
  const { messages, isLoading, sendMessage } = useChat();

  return (
    <div>
      <MessageList messages={messages} isLoading={isLoading} />
      <MessageInput onSend={sendMessage} disabled={isLoading} />
    </div>
  );
}
