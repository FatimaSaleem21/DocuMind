import { apiFetch } from "./client";

interface ChatResponse {
  answer: string;
  sources: number[];
}

export function postChatMessage(question: string): Promise<ChatResponse> {
  return apiFetch("/chat/", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}
