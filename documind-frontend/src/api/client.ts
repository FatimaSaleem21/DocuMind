const API_URL = import.meta.env.VITE_API_URL;

function flattenErrorBody(body: unknown): string | null {
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

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, options);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(flattenErrorBody(body) ?? `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function get<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function post<T>(path: string, body: FormData): Promise<T> {
  return request<T>(path, { method: "POST", body });
}
