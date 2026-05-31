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
      <div className="flex justify-between items-baseline mb-10">
        <div>
          <span className="font-mono text-sm text-[#445566]">~/interview $</span>
          <span className="font-mono text-2xl font-bold text-[#00e5ff] tracking-tight ml-2">loopprep</span>
        </div>
        <span
          className={`font-mono text-xs px-2 py-0.5 border rounded-sm ${
            health === "ok"
              ? "border-[#00ff87] text-[#00ff87]"
              : "border-[#ff4560] text-[#ff4560]"
          }`}
        >
          api: {health}
        </span>
      </div>

      {view === "setup" && (
        <section className="bg-[#111822] border border-[#1e2d3d] rounded-sm p-6">
          <div>
            <label className="block font-mono text-xs text-[#445566] uppercase tracking-widest mb-2">
              // job description
            </label>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the full job description here…"
              className="w-full min-h-40 bg-[#0d1520] border border-[#1e2d3d] rounded-sm p-3 font-mono text-sm text-[#e8edf3] resize-none placeholder:text-[#445566] focus:outline-none focus:border-[#00e5ff] transition-colors"
            />
          </div>

          <div className="grid grid-cols-2 gap-3 mt-4">
            <div>
              <label className="block font-mono text-xs text-[#445566] uppercase tracking-widest mb-1.5">
                company
              </label>
              <input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="Google"
                className="w-full bg-[#0d1520] border border-[#1e2d3d] rounded-sm px-3 py-2.5 font-mono text-sm text-[#e8edf3] placeholder:text-[#445566] focus:outline-none focus:border-[#00e5ff] transition-colors"
              />
            </div>
            <div>
              <label className="block font-mono text-xs text-[#445566] uppercase tracking-widest mb-1.5">
                role
              </label>
              <input
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="Software Engineer L4"
                className="w-full bg-[#0d1520] border border-[#1e2d3d] rounded-sm px-3 py-2.5 font-mono text-sm text-[#e8edf3] placeholder:text-[#445566] focus:outline-none focus:border-[#00e5ff] transition-colors"
              />
            </div>
          </div>

          <button
            onClick={handleStart}
            disabled={loading || jobDescription.length < 10}
            className={`mt-5 w-full py-3 rounded-sm font-mono text-sm uppercase tracking-widest transition-colors ${
              loading || jobDescription.length < 10
                ? "border border-[#1e2d3d] text-[#445566] cursor-not-allowed bg-transparent"
                : "border border-[#00e5ff] text-[#00e5ff] bg-transparent hover:bg-[#00e5ff]/10"
            }`}
          >
            {loading ? (
              <>
                <span className="text-[#445566]">[</span>
                <span className="blink text-[#445566]"> running </span>
                <span className="text-[#445566]">]</span>
                <span className="ml-2">building your interview...</span>
              </>
            ) : (
              "start interview"
            )}
          </button>

          {loading && (
            <p className="font-mono text-xs text-[#445566] text-center mt-3">
              research agent + format agent running in parallel — ~15s
            </p>
          )}

          {error && <p className="font-mono text-xs text-[#ff4560] mt-2">{error}</p>}
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
