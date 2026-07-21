import { useEffect, useRef } from "react";
import type { ChatMessage } from "../../types/chat";
import { AnswerReceipt } from "./AnswerReceipt";
import { UserMessage } from "./UserMessage";
import styles from "./MessageList.module.css";

export function MessageList({ messages, isLoading }: { messages: ChatMessage[]; isLoading: boolean }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div>
      {messages.length === 0 && <p className={styles.hint}>no questions asked yet — try one below</p>}
      {messages.map((m) =>
        m.role === "user" ? (
          <UserMessage key={m.id} content={m.content} />
        ) : (
          <AnswerReceipt key={m.id} content={m.content} sources={m.sources} />
        ),
      )}
      {isLoading && <p className={styles.hint}>thinking…</p>}
      <div ref={bottomRef} />
    </div>
  );
}
