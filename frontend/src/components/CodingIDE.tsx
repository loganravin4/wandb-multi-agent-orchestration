import { useRef, useState } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import {
  type AnswerResponse,
  type Question,
  executeCode,
  getHint,
  submitAnswer,
} from "../api/client";

function buildStarter(question: Question): string {
  if (question.function_signature) {
    return `${question.function_signature}\n    # Write your solution here\n    pass\n\n\n# Test your solution\n`;
  }
  return `def solution():\n    # Write your solution here\n    pass\n\n\n# Test your solution\nprint(solution())\n`;
}

interface Props {
  sessionId: string;
  question: Question;
  questionIndex: number;
  totalQuestions: number;
  onNext: (result: AnswerResponse) => void;
}

type RunState = "idle" | "running" | "done";
type SubmitState = "idle" | "submitting" | "scored";

export default function CodingIDE({ sessionId, question, questionIndex, totalQuestions, onNext }: Props) {
  const [code, setCode] = useState(() => buildStarter(question));
  const [runState, setRunState] = useState<RunState>("idle");
  const [output, setOutput] = useState<{ stdout: string; stderr: string; exit_code: number; timed_out: boolean } | null>(null);
  const [submitState, setSubmitState] = useState<SubmitState>("idle");
  const [scores, setScores] = useState<AnswerResponse | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [hintLoading, setHintLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const startRef = useRef(Date.now());

  async function handleRun() {
    setRunState("running");
    setOutput(null);
    try {
      const result = await executeCode(sessionId, code);
      setOutput(result);
    } catch {
      setOutput({ stdout: "", stderr: "Execution failed — backend may not be ready.", exit_code: 1, timed_out: false });
    } finally {
      setRunState("done");
    }
  }

  async function handleSubmit() {
    setSubmitState("submitting");
    setError(null);

    const outputSection = output
      ? `\n\n# --- Run Output ---\n${output.stdout || ""}${output.stderr ? `# stderr:\n${output.stderr}` : ""}`
      : "\n\n# --- Not run before submission ---";
    const transcript = `${code}${outputSection}`;
    const duration = (Date.now() - startRef.current) / 1000;

    try {
      const result = await submitAnswer(sessionId, {
        transcript,
        duration_seconds: Math.max(duration, 1),
        question_index: questionIndex,
      });
      setScores(result);
      setSubmitState("scored");
    } catch {
      setError("Submit failed — try again.");
      setSubmitState("idle");
    }
  }

  async function handleHint() {
    setHintLoading(true);
    try {
      const { hint: h } = await getHint(sessionId, questionIndex, code);
      setHint(h);
    } catch {
      setHint("Hint unavailable right now.");
    } finally {
      setHintLoading(false);
    }
  }

  const hasOutput = output !== null;
  const outputText = output
    ? [output.stdout, output.stderr].filter(Boolean).join("\n").trim() || "(no output)"
    : "";

  return (
    <div className="fixed inset-0 bg-[#0a0e13] flex flex-col" style={{ zIndex: 50 }}>
      {/* Top bar */}
      <div className="h-12 border-b border-[#1e2d3d] flex items-center justify-between px-5 shrink-0">
        <div className="flex items-center gap-4">
          <span className="font-mono text-xs text-[#445566]">~/interview $</span>
          <span className="font-mono text-xl font-bold text-[#00e5ff] tracking-tight">loopprep</span>
          <span className="font-mono text-xs text-[#445566]">
            question {questionIndex + 1}/{totalQuestions}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleSubmit}
            disabled={submitState !== "idle"}
            className={`font-mono text-xs uppercase tracking-widest px-4 py-1.5 rounded-sm border transition-colors ${
              submitState === "submitting"
                ? "border-[#445566] text-[#445566] cursor-not-allowed"
                : submitState === "scored"
                ? "border-[#1e2d3d] text-[#1e2d3d] cursor-not-allowed"
                : "border-[#00ff87] text-[#00ff87] hover:bg-[#00ff87]/10"
            }`}
          >
            {submitState === "submitting" ? "scoring…" : submitState === "scored" ? "submitted ✓" : "submit"}
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left panel — question info or results after submit */}
        <div className="w-2/5 border-r border-[#1e2d3d] overflow-y-auto p-6 flex flex-col gap-5">

          {submitState === "scored" && scores ? (
            /* ── Results view (replaces question when scored) ── */
            <>
              <div className="flex gap-2 flex-wrap">
                <Badge label={question.type} color="#00e5ff" />
                {question.subtype && <Badge label={question.subtype.replace(/_/g, " ")} color="#445566" />}
                <Badge
                  label={question.difficulty}
                  color={question.difficulty === "hard" ? "#ff4560" : question.difficulty === "medium" ? "#ffb300" : "#00ff87"}
                />
              </div>

              <div className="flex gap-3">
                <ScoreTile label="content" value={scores.content_score} />
              </div>

              <div className="border-l-2 border-[#00e5ff] pl-4 py-1">
                <p className="font-sans text-sm text-[#e8edf3] leading-relaxed m-0">
                  {scores.feedback}
                </p>
              </div>

              <button
                onClick={() => onNext(scores)}
                className="font-mono text-sm uppercase tracking-widest px-4 py-2.5 rounded-sm border border-[#00e5ff] text-[#00e5ff] hover:bg-[#00e5ff]/10 transition-colors w-full"
              >
                {scores.session_complete ? "view report →" : "next question →"}
              </button>

              {error && <p className="font-mono text-xs text-[#ff4560]">{error}</p>}
            </>
          ) : (
            /* ── Question view ── */
            <>
              <div className="flex gap-2 flex-wrap">
                <Badge label={question.type} color="#00e5ff" />
                {question.subtype && <Badge label={question.subtype.replace(/_/g, " ")} color="#445566" />}
                <Badge
                  label={question.difficulty}
                  color={question.difficulty === "hard" ? "#ff4560" : question.difficulty === "medium" ? "#ffb300" : "#00ff87"}
                />
              </div>

              <div>
                <p className="font-mono text-xs text-[#445566] uppercase tracking-widest mb-2">// description</p>
                <p className="font-sans text-sm leading-relaxed text-[#e8edf3] m-0">{question.text}</p>
              </div>

              {question.function_signature && (
                <div>
                  <p className="font-mono text-xs text-[#445566] uppercase tracking-widest mb-2">// signature</p>
                  <pre className="font-mono text-xs text-[#00e5ff] bg-[#0d1520] border border-[#1e2d3d] rounded-sm p-3 m-0 whitespace-pre-wrap">
                    {question.function_signature}
                  </pre>
                </div>
              )}

              {question.examples && question.examples.length > 0 && (
                <div>
                  <p className="font-mono text-xs text-[#445566] uppercase tracking-widest mb-3">// examples</p>
                  <div className="flex flex-col gap-3">
                    {question.examples.map((ex, i) => (
                      <div key={i} className="bg-[#0d1520] border border-[#1e2d3d] rounded-sm p-3">
                        <p className="font-mono text-xs text-[#445566] mb-2">example {i + 1}</p>
                        <div className="flex flex-col gap-1">
                          <div>
                            <span className="font-mono text-xs text-[#8899aa]">input:  </span>
                            <span className="font-mono text-xs text-[#e8edf3]">{ex.input}</span>
                          </div>
                          <div>
                            <span className="font-mono text-xs text-[#8899aa]">output: </span>
                            <span className="font-mono text-xs text-[#00ff87]">{ex.output}</span>
                          </div>
                          {ex.explanation && (
                            <p className="font-sans text-xs text-[#445566] mt-1 m-0">{ex.explanation}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {question.constraints && question.constraints.length > 0 && (
                <div>
                  <p className="font-mono text-xs text-[#445566] uppercase tracking-widest mb-2">// constraints</p>
                  <ul className="m-0 p-0 list-none flex flex-col gap-1">
                    {question.constraints.map((c, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="font-mono text-xs text-[#445566] shrink-0">•</span>
                        <span className="font-mono text-xs text-[#8899aa]">{c}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {hint && (
                <div className="border-l-2 border-[#ffb300] pl-4 py-2">
                  <span className="font-mono text-xs text-[#ffb300] block mb-1">&gt; hint</span>
                  <span className="font-sans text-sm text-[#8899aa] leading-relaxed">{hint}</span>
                </div>
              )}

              <button
                onClick={handleHint}
                disabled={hintLoading}
                className={`font-mono text-xs uppercase tracking-widest px-3 py-1.5 rounded-sm border w-fit transition-colors ${
                  hintLoading
                    ? "border-[#1e2d3d] text-[#445566] cursor-not-allowed"
                    : "border-[#ffb300] text-[#ffb300] hover:bg-[#ffb300]/10"
                }`}
              >
                {hintLoading ? "…" : hint ? "another hint" : "get hint"}
              </button>
            </>
          )}
        </div>

        {/* Right panel — editor + output */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Editor toolbar */}
          <div className="h-9 border-b border-[#1e2d3d] flex items-center justify-between px-4 shrink-0 bg-[#0d1520]">
            <span className="font-mono text-xs text-[#445566]">python 3</span>
            <button
              onClick={handleRun}
              disabled={runState === "running" || submitState === "scored"}
              className={`font-mono text-xs uppercase tracking-widest px-3 py-1 rounded-sm border transition-colors ${
                runState === "running" || submitState === "scored"
                  ? "border-[#1e2d3d] text-[#445566] cursor-not-allowed"
                  : "border-[#00e5ff] text-[#00e5ff] hover:bg-[#00e5ff]/10"
              }`}
            >
              {runState === "running" ? "running…" : "▶ run"}
            </button>
          </div>

          {/* CodeMirror editor */}
          <div className="flex-1 overflow-hidden">
            <CodeMirror
              value={code}
              onChange={setCode}
              extensions={[python()]}
              theme="dark"
              readOnly={submitState === "scored"}
              style={{ height: "100%", fontSize: "13px" }}
              basicSetup={{
                lineNumbers: true,
                highlightActiveLineGutter: true,
                foldGutter: true,
                autocompletion: true,
                bracketMatching: true,
              }}
            />
          </div>

          {/* Output terminal */}
          <div
            className={`border-t border-[#1e2d3d] bg-[#0a0e13] overflow-y-auto transition-all duration-200 ${
              hasOutput ? "h-44" : "h-9"
            }`}
          >
            <div className="flex items-center gap-2 px-4 h-9 border-b border-[#1e2d3d] shrink-0">
              <span className="font-mono text-xs text-[#445566]">output</span>
              {hasOutput && output!.exit_code === 0 && !output!.timed_out && (
                <span className="font-mono text-xs text-[#00ff87]">✓ exited 0</span>
              )}
              {hasOutput && (output!.exit_code !== 0 || output!.timed_out) && (
                <span className="font-mono text-xs text-[#ff4560]">
                  {output!.timed_out ? "timed out" : `exited ${output!.exit_code}`}
                </span>
              )}
            </div>
            {hasOutput && (
              <pre className="font-mono text-xs text-[#e8edf3] p-4 m-0 whitespace-pre-wrap leading-relaxed">
                {outputText}
              </pre>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span className="font-mono text-xs tracking-wide" style={{ color }}>
      [{label}]
    </span>
  );
}

function ScoreTile({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="bg-[#0d1520] border border-[#1e2d3d] rounded-sm p-2 text-center">
      <span className={`font-mono text-xl font-bold ${value != null ? scoreColor(value) : "text-[#445566]"}`}>
        {value != null ? value.toFixed(1) : "—"}
      </span>
      <span className="font-mono text-xs text-[#445566] ml-0.5">/10</span>
      <div className="font-mono text-xs text-[#445566] uppercase tracking-widest mt-0.5">{label}</div>
    </div>
  );
}

function scoreColor(value: number): string {
  if (value >= 7) return "text-[#00ff87]";
  if (value >= 5) return "text-[#ffb300]";
  return "text-[#ff4560]";
}
