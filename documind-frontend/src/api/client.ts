export const API_URL = import.meta.env.VITE_API_URL;

const SESSION_STORAGE_KEY = "documind_session_id";

// Stable per-browser id so the backend scopes documents/chat to this visitor.
// Not authentication — just demo isolation so uploads aren't shared globally.
export function getSessionId(): string {
  let id = localStorage.getItem(SESSION_STORAGE_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(SESSION_STORAGE_KEY, id);
  }
  return id;
}

export function flattenErrorBody(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const messages: string[] = [];
  for (const value of Object.values(body as Record<string, unknown>)) {
    if (Array.isArray(value)) {
      messages.push(...value.map(String));
    } else if (typeof value === "string") {
      messages.push(value);
    }
  }
  return messages.length > 0 ? messages.join(" ") : null;
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const isFormData = options?.body instanceof FormData;
  const headers: Record<string, string> = {
    "X-Session-Id": getSessionId(),
    // Let the browser set the multipart boundary for FormData uploads.
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options?.headers as Record<string, string> | undefined),
  };

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(flattenErrorBody(body) ?? `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function get<T>(path: string): Promise<T> {
  return apiFetch<T>(path);
}

export function post<T>(path: string, body: FormData): Promise<T> {
  return apiFetch<T>(path, { method: "POST", body });
}
