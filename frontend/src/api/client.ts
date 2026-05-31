const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type Example = {
  input: string;
  output: string;
  explanation?: string;
};

export type Question = {
  index: number;
  type: "coding" | "behavioral" | "system_design" | "brain_teaser";
  subtype: string;
  text: string;
  difficulty: "easy" | "medium" | "hard";
  function_signature?: string;
  examples?: Example[];
  constraints?: string[];
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

export type AnswerPayload = {
  transcript: string;
  duration_seconds: number;
  question_index: number;
};

export type AnswerResponse = {
  content_score: number;
  delivery_score: number;
  wpm: number;
  filler_rate: number;
  feedback: string;
  next_question: Question | null;
  session_complete: boolean;
};

export type ReportResponse = {
  summary: string;
  strengths: string[];
  areas_to_improve: string[];
  next_steps: string[];
  avg_content_score: number;
  avg_delivery_score: number;
  avg_overall: number;
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
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function submitAnswer(
  sessionId: string,
  payload: AnswerPayload,
): Promise<AnswerResponse> {
  return request(`/sessions/${sessionId}/answer`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getHint(
  sessionId: string,
  questionIndex: number,
  transcript: string,
): Promise<{ hint: string }> {
  return request(`/sessions/${sessionId}/hint`, {
    method: "POST",
    body: JSON.stringify({ question_index: questionIndex, transcript }),
  });
}

export type ExecuteResponse = {
  stdout: string;
  stderr: string;
  exit_code: number;
  timed_out: boolean;
};

export async function executeCode(
  sessionId: string,
  code: string,
): Promise<ExecuteResponse> {
  return request(`/sessions/${sessionId}/execute`, {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export async function getReport(sessionId: string): Promise<ReportResponse> {
  return request(`/sessions/${sessionId}/report`);
}
