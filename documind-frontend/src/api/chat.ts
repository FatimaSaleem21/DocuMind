import { API_URL, flattenErrorBody, getSessionId } from "./client";

export async function streamChatMessage(
  question: string,
  onToken: (content: string) => void,
  onDone: (sources: number[]) => void,
  onError: (message: string) => void,
) {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/chat/stream/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Session-Id": getSessionId() },
      body: JSON.stringify({ question }),
    });
  } catch {
    onError("Network error — check your connection and try again.");
    return;
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    onError(flattenErrorBody(body) ?? `Request failed with status ${res.status}`);
    return;
  }

  if (!res.body) {
    onError("No response body");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";

      for (const raw of events) {
        if (!raw.trim()) continue;
        const eventMatch = raw.match(/event: (\w+)/);
        const dataMatch = raw.match(/data: (.+)/);
        if (!eventMatch || !dataMatch) continue;

        const data = JSON.parse(dataMatch[1]);
        if (eventMatch[1] === "token") onToken(data.content);
        if (eventMatch[1] === "done") onDone(data.sources);
        if (eventMatch[1] === "error") onError(data.message);
      }
    }
  } catch {
    onError("Connection lost while streaming — try again.");
  }
}
