export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: number[];
  isError?: boolean;
}
