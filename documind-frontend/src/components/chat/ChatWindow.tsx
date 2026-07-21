import { useChat } from "../../hooks/useChat";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";
import styles from "./ChatWindow.module.css";

export function ChatWindow() {
  const { messages, isLoading, sendMessage } = useChat();

  return (
    <div className={styles.panel}>
      <div className={styles.messages}>
        <MessageList messages={messages} isLoading={isLoading} />
      </div>
      <div className={styles.inputArea}>
        <MessageInput onSend={sendMessage} disabled={isLoading} />
      </div>
    </div>
  );
}
