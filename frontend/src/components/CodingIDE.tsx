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

const STARTER = `def solution():
    # Write your solution here
    pass


# Test your solution
print(solution())
`;

interface Props {
  sessionId: string;
  question: Question;
  questionIndex: number;
  totalQuestions: number;
  onScored: (result: AnswerResponse) => void;
}

type RunState = "idle" | "running" | "done";
type SubmitState = "idle" | "submitting" | "scored";

export default function CodingIDE({ sessionId, question, questionIndex, totalQuestions, onScored }: Props) {
  const [code, setCode] = useState(STARTER);
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
      ? `\n\n# --- Output ---\n${output.stdout || ""}${output.stderr ? `# stderr: ${output.stderr}` : ""}`
      : "";
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
      onScored(result);
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
          {submitState === "scored" && scores && (
            <div className="flex gap-3">
              <span className="font-mono text-xs">
                <span className="text-[#445566]">content </span>
                <span className={scoreColor(scores.content_score)}>{scores.content_score.toFixed(1)}</span>
                <span className="text-[#445566]">/10</span>
              </span>
              <span className="font-mono text-xs">
                <span className="text-[#445566]">delivery </span>
                <span className={scoreColor(scores.delivery_score)}>{scores.delivery_score.toFixed(1)}</span>
                <span className="text-[#445566]">/10</span>
              </span>
            </div>
          )}
          {submitState !== "scored" && (
            <button
              onClick={handleSubmit}
              disabled={submitState === "submitting"}
              className={`font-mono text-xs uppercase tracking-widest px-4 py-1.5 rounded-sm border transition-colors ${
                submitState === "submitting"
                  ? "border-[#445566] text-[#445566] cursor-not-allowed"
                  : "border-[#00ff87] text-[#00ff87] hover:bg-[#00ff87]/10"
              }`}
            >
              {submitState === "submitting" ? "scoring…" : "submit"}
            </button>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left panel — question */}
        <div className="w-2/5 border-r border-[#1e2d3d] overflow-y-auto p-6 flex flex-col gap-5">
          {/* Badges */}
          <div className="flex gap-2 flex-wrap">
            <Badge label={question.type} color="#00e5ff" />
            {question.subtype && <Badge label={question.subtype.replace(/_/g, " ")} color="#445566" />}
            <Badge
              label={question.difficulty}
              color={question.difficulty === "hard" ? "#ff4560" : question.difficulty === "medium" ? "#ffb300" : "#445566"}
            />
          </div>

          {/* Question text */}
          <p className="font-mono text-sm leading-relaxed text-[#e8edf3] m-0 whitespace-pre-wrap">
            {question.text}
          </p>

          {/* Hint */}
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

          {/* Scores panel (after submit) */}
          {submitState === "scored" && scores && (
            <div className="border border-[#1e2d3d] rounded-sm p-4 bg-[#111822]">
              <p className="font-mono text-xs text-[#445566] uppercase tracking-widest mb-3">// feedback</p>
              <div className="grid grid-cols-2 gap-2 mb-3">
                <ScoreTile label="content" value={scores.content_score} />
                <ScoreTile label="delivery" value={scores.delivery_score} />
                <ScoreTile label="wpm" value={scores.wpm} unit="" fixed={0} dimColor />
                <ScoreTile label="fillers" value={scores.filler_rate * 100} unit="%" fixed={1} dimColor={scores.filler_rate <= 0.1} />
              </div>
              <p className="font-sans text-sm text-[#8899aa] leading-relaxed m-0">
                <span className="font-mono text-[#00e5ff] mr-1">&gt;</span>
                {scores.feedback}
              </p>
              {error && <p className="font-mono text-xs text-[#ff4560] mt-2">{error}</p>}
            </div>
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

function ScoreTile({
  label,
  value,
  unit = "/10",
  fixed = 1,
  dimColor = false,
}: {
  label: string;
  value: number;
  unit?: string;
  fixed?: number;
  dimColor?: boolean;
}) {
  const color = dimColor ? "text-[#8899aa]" : scoreColor(value, unit === "/10");
  return (
    <div className="bg-[#0d1520] border border-[#1e2d3d] rounded-sm p-2 text-center">
      <span className={`font-mono text-xl font-bold ${color}`}>{value.toFixed(fixed)}</span>
      <span className="font-mono text-xs text-[#445566] ml-0.5">{unit}</span>
      <div className="font-mono text-xs text-[#445566] uppercase tracking-widest mt-0.5">{label}</div>
    </div>
  );
}

function scoreColor(value: number, tenScale = true): string {
  const threshold = tenScale ? [7, 5] : [70, 50];
  if (value >= threshold[0]) return "text-[#00ff87]";
  if (value >= threshold[1]) return "text-[#ffb300]";
  return "text-[#ff4560]";
}
