const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type Question = {
  index: number;
  type: "coding" | "behavioral" | "system_design";
  text: string;
  difficulty: "easy" | "medium" | "hard";
};

export type CreateSessionPayload = {
  job_description: string;
  company?: string;
  role?: string;
  seniority?: string;
};

export type CreateSessionResponse = {
  session_id: string;
  phase: string;
  questions: Question[];
};

export type SessionResponse = {
  session_id: string;
  phase: string;
  current_question: Question | null;
  questions: Question[];
  results: unknown[];
  report: Record<string, unknown> | null;
  error: string | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function checkHealth(): Promise<{ status: string }> {
  return request("/health");
}

export async function createSession(
  payload: CreateSessionPayload,
): Promise<CreateSessionResponse> {
  return request("/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  return request(`/sessions/${sessionId}`);
}

export async function transcribeAudio(
  sessionId: string,
  file: File,
): Promise<{ session_id: string; transcript: string }> {
  const form = new FormData();
  form.append("audio", file);
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/transcribe`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}
