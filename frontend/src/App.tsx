import { useEffect, useState } from "react";
import {
  checkHealth,
  createSession,
  type CreateSessionResponse,
  type Question,
} from "./api/client";

export default function App() {
  const [health, setHealth] = useState<string>("checking…");
  const [jobDescription, setJobDescription] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<CreateSessionResponse | null>(null);

  useEffect(() => {
    checkHealth()
      .then((r) => setHealth(r.status))
      .catch(() => setHealth("unreachable"));
  }, []);

  async function handleStart() {
    setLoading(true);
    setError(null);
    try {
      const result = await createSession({
        job_description: jobDescription,
        company,
        role,
      });
      setSession(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start session");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Multi-Agent Orchestration</h1>
      <p>
        API status: <strong>{health}</strong>
      </p>

      {!session ? (
        <section className="card">
          <h2>Start a session</h2>
          <label>
            Job description
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste a job description…"
            />
          </label>
          <label>
            Company
            <input
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Acme Corp"
              style={{ width: "100%", marginTop: "0.25rem", padding: "0.5rem" }}
            />
          </label>
          <label>
            Role
            <input
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="Software Engineer"
              style={{ width: "100%", marginTop: "0.25rem", padding: "0.5rem" }}
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button
            type="button"
            disabled={loading || jobDescription.length < 10}
            onClick={handleStart}
          >
            {loading ? "Running agents…" : "Create session"}
          </button>
        </section>
      ) : (
        <section className="card">
          <h2>Session {session.session_id.slice(0, 8)}…</h2>
          <p>Phase: {session.phase}</p>
          <ol>
            {session.questions.map((q: Question) => (
              <li key={q.index}>
                <strong>{q.type}</strong> ({q.difficulty}): {q.text}
              </li>
            ))}
          </ol>
        </section>
      )}
    </main>
  );
}
