import { useEffect, useRef } from "react";
import type { ChatMessage } from "../../types/chat";
import { AnswerReceipt } from "./AnswerReceipt";
import { UserMessage } from "./UserMessage";

export function MessageList({ messages, isLoading }: { messages: ChatMessage[]; isLoading: boolean }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div>
      {messages.length === 0 && (
        <p style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "#8A857A" }}>
          no questions asked yet — try one below
        </p>
      )}
      {messages.map((m) =>
        m.role === "user" ? (
          <UserMessage key={m.id} content={m.content} />
        ) : (
          <AnswerReceipt key={m.id} content={m.content} sources={m.sources} />
        ),
      )}
      {isLoading && <p style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "#8A857A" }}>thinking…</p>}
      <div ref={bottomRef} />
    </div>
  );
}
