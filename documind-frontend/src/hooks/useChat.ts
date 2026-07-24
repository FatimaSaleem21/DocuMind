import { useState } from "react";
import { streamChatMessage } from "../api/chat";
import type { ChatMessage } from "../types/chat";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  async function sendMessage(question: string) {
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: question };
    const assistantId = crypto.randomUUID();
    setMessages((prev) => [...prev, userMsg, { id: assistantId, role: "assistant", content: "" }]);
    setIsLoading(true);

    await streamChatMessage(
      question,
      (token) => {
        setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + token } : m)));
      },
      (sources) => {
        setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, sources } : m)));
        setIsLoading(false);
      },
      (errorMessage) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: errorMessage || "Something went wrong — try asking again.", isError: true }
              : m,
          ),
        );
        setIsLoading(false);
      },
    );
  }

  return { messages, isLoading, sendMessage };
}
