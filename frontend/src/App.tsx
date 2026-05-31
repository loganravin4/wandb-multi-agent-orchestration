import { useEffect, useState } from "react";
import {
  checkHealth,
  createSession,
  type CreateSessionResponse,
  type ReportResponse,
} from "./api/client";
import Interview from "./components/Interview";
import Report from "./components/Report";

type View = "setup" | "interview" | "report";

export default function App() {
  const [health, setHealth] = useState<string>("checking…");
  const [view, setView] = useState<View>("setup");

  // Setup form
  const [jobDescription, setJobDescription] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Session + report data
  const [session, setSession] = useState<CreateSessionResponse | null>(null);
  const [report, setReport] = useState<ReportResponse | null>(null);

  useEffect(() => {
    checkHealth()
      .then((r) => setHealth(r.status))
      .catch(() => setHealth("unreachable"));
  }, []);

  async function handleStart() {
    setLoading(true);
    setError(null);
    try {
      const result = await createSession({ job_description: jobDescription, company, role });
      setSession(result);
      setView("interview");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start session");
    } finally {
      setLoading(false);
    }
  }

  function handleComplete(r: ReportResponse) {
    setReport(r);
    setView("report");
  }

  function handleRestart() {
    setSession(null);
    setReport(null);
    setJobDescription("");
    setCompany("");
    setRole("");
    setView("setup");
  }

  return (
    <main>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h1 style={{ margin: "0 0 0.25rem" }}>LoopPrep</h1>
        <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>API: {health}</span>
      </div>
      <p style={{ margin: "0 0 1.5rem", color: "#64748b" }}>AI-powered mock interview coach</p>

      {view === "setup" && (
        <section className="card">
          <h2 style={{ margin: "0 0 1rem" }}>New Session</h2>
          <label style={{ display: "block", marginBottom: "0.75rem" }}>
            <span style={{ fontWeight: 600 }}>Job Description</span>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the full job description here…"
              style={{ marginTop: "0.4rem", minHeight: 160 }}
            />
          </label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "1rem" }}>
            <label style={{ display: "block" }}>
              <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>Company</span>
              <input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="Google"
                style={{ display: "block", width: "100%", marginTop: "0.3rem", padding: "0.5rem 0.75rem", border: "1px solid #cbd5e1", borderRadius: 8, font: "inherit" }}
              />
            </label>
            <label style={{ display: "block" }}>
              <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>Role</span>
              <input
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="Software Engineer L4"
                style={{ display: "block", width: "100%", marginTop: "0.3rem", padding: "0.5rem 0.75rem", border: "1px solid #cbd5e1", borderRadius: 8, font: "inherit" }}
              />
            </label>
          </div>
          {error && <p className="error">{error}</p>}
          <button
            onClick={handleStart}
            disabled={loading || jobDescription.length < 10}
            style={{ width: "100%", padding: "0.75rem", fontSize: "1rem" }}
          >
            {loading ? "Researching company + building question queue…" : "Start Interview"}
          </button>
          {loading && (
            <p style={{ color: "#64748b", fontSize: "0.85rem", textAlign: "center", marginBottom: 0 }}>
              Research Agent and Format Agent are running in parallel — this takes ~15s
            </p>
          )}
        </section>
      )}

      {view === "interview" && session && (
        <Interview
          sessionId={session.session_id}
          questions={session.questions}
          onComplete={handleComplete}
        />
      )}

      {view === "report" && report && (
        <Report report={report} onRestart={handleRestart} />
      )}
    </main>
  );
}
