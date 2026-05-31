import { useRef, useState } from "react";
import {
  type AnswerResponse,
  type Question,
  type ReportResponse,
  getHint,
  getReport,
  submitAnswer,
  transcribeAudio,
} from "../api/client";
import CodingIDE from "./CodingIDE";

type Phase =
  | "idle"
  | "recording"
  | "processing"
  | "reviewing"
  | "submitting"
  | "scored";

interface Props {
  sessionId: string;
  questions: Question[];
  onComplete: (report: ReportResponse) => void;
}

export default function Interview({ sessionId, questions, onComplete }: Props) {
  const [questionIndex, setQuestionIndex] = useState(0);
  const [phase, setPhase] = useState<Phase>("idle");
  const [transcript, setTranscript] = useState("");
  const [duration, setDuration] = useState(0);
  const [scores, setScores] = useState<AnswerResponse | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [hintLoading, setHintLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [mode, setMode] = useState<"voice" | "text">("voice");
  const [typedAnswer, setTypedAnswer] = useState("");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startTimeRef = useRef(0);

  const currentQuestion = questions[questionIndex];

  async function startRecording() {
    setError(null);
    setHint(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const dur = (Date.now() - startTimeRef.current) / 1000;
        setDuration(dur);
        setPhase("processing");
        try {
          const file = new File([blob], "answer.webm", { type: "audio/webm" });
          const { transcript: t } = await transcribeAudio(sessionId, file);
          setTranscript(t);
          setPhase("reviewing");
        } catch {
          setError("Transcription failed — try recording again.");
          setPhase("idle");
        }
      };

      mediaRecorderRef.current = mr;
      startTimeRef.current = Date.now();
      mr.start();
      setPhase("recording");
    } catch {
      setError("Microphone access denied. Allow microphone and try again.");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
  }

  function handleTextSubmitReview() {
    setTranscript(typedAnswer);
    setDuration(60);
    setPhase("reviewing");
  }

  function handleModeSwitch(newMode: "voice" | "text") {
    setMode(newMode);
    if (phase !== "scored") {
      setPhase("idle");
      setTranscript("");
      setTypedAnswer("");
      setError(null);
    }
  }

  async function handleSubmit() {
    setPhase("submitting");
    setError(null);
    try {
      const result = await submitAnswer(sessionId, {
        transcript,
        duration_seconds: duration,
        question_index: questionIndex,
      });
      setScores(result);
      setPhase("scored");

      if (result.session_complete) {
        setReportLoading(true);
        try {
          const report = await getReport(sessionId);
          onComplete(report);
        } catch {
          setError("Session complete — report endpoint not ready yet.");
        } finally {
          setReportLoading(false);
        }
      }
    } catch {
      setError("Answer endpoint not ready yet — your teammates are on it.");
      setPhase("reviewing");
    }
  }

  async function handleHint() {
    setHintLoading(true);
    try {
      const { hint: h } = await getHint(sessionId, questionIndex, transcript);
      setHint(h);
    } catch {
      setHint("Hint unavailable right now.");
    } finally {
      setHintLoading(false);
    }
  }

  function nextQuestion() {
    setQuestionIndex((i) => i + 1);
    setPhase("idle");
    setTranscript("");
    setTypedAnswer("");
    setScores(null);
    setHint(null);
    setError(null);
  }

  const btnBase =
    "font-mono text-sm uppercase tracking-widest bg-transparent py-2 px-4 rounded-sm border transition-colors";

  // Coding questions get the full-screen IDE treatment
  if (currentQuestion.type === "coding") {
    return (
      <CodingIDE
        key={questionIndex}
        sessionId={sessionId}
        question={currentQuestion}
        questionIndex={questionIndex}
        totalQuestions={questions.length}
        onScored={async (result) => {
          if (result.session_complete) {
            try {
              const report = await getReport(sessionId);
              onComplete(report);
            } catch {
              // report not ready yet — Interview will show next question
            }
          } else {
            nextQuestion();
          }
        }}
      />
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-center mb-5">
        <span className="font-mono text-xs text-[#445566]">// interview</span>
        <span className="font-mono text-xs text-[#445566]">
          question {questionIndex + 1}/{questions.length}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-px bg-[#1e2d3d] mb-6">
        <div
          className="h-full bg-[#00e5ff] transition-all duration-500"
          style={{
            width: `${((questionIndex + (phase === "scored" ? 1 : 0)) / questions.length) * 100}%`,
          }}
        />
      </div>

      {/* Question card */}
      <div className="bg-[#111822] border-l-2 border-[#00e5ff] pl-5 pr-4 py-4 mb-4">
        <div className="flex gap-3 mb-3 flex-wrap">
          <Badge type={currentQuestion.type} />
          {currentQuestion.subtype && <Badge type={currentQuestion.subtype} variant="subtype" />}
          <Badge type={currentQuestion.difficulty} />
        </div>
        <p className="font-mono text-[0.95rem] leading-relaxed text-[#e8edf3]">
          {currentQuestion.text}
        </p>
      </div>

      {/* Hint panel */}
      {hint && (
        <div className="border-l-2 border-[#ffb300] pl-4 py-2 mb-3">
          <span className="font-mono text-xs text-[#ffb300] mr-2">&gt; hint:</span>
          <span className="font-sans text-sm text-[#8899aa]">{hint}</span>
        </div>
      )}

      {/* Action card */}
      <div className="bg-[#111822] border border-[#1e2d3d] rounded-sm p-4">
        {/* Mode toggle (preserved logic; not in design spec) */}
        {phase !== "scored" && (
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => handleModeSwitch("voice")}
              className={`font-mono text-xs uppercase tracking-widest px-3 py-1.5 rounded-sm border transition-colors ${
                mode === "voice"
                  ? "border-[#00e5ff] text-[#00e5ff] bg-[#00e5ff]/10"
                  : "border-[#1e2d3d] text-[#445566] bg-transparent hover:text-[#8899aa]"
              }`}
            >
              voice
            </button>
            <button
              onClick={() => handleModeSwitch("text")}
              className={`font-mono text-xs uppercase tracking-widest px-3 py-1.5 rounded-sm border transition-colors ${
                mode === "text"
                  ? "border-[#00e5ff] text-[#00e5ff] bg-[#00e5ff]/10"
                  : "border-[#1e2d3d] text-[#445566] bg-transparent hover:text-[#8899aa]"
              }`}
            >
              text
            </button>
          </div>
        )}

        {mode === "voice" && phase === "idle" && (
          <button
            onClick={startRecording}
            className="font-mono text-sm uppercase tracking-widest border border-[#00ff87] text-[#00ff87] bg-transparent py-2.5 px-5 rounded-sm hover:bg-[#00ff87]/10 transition-colors"
          >
            ▶ start recording
          </button>
        )}

        {mode === "voice" && phase === "recording" && (
          <div className="flex items-center gap-3">
            <span className="font-mono text-sm text-[#ff4560]">▶ recording</span>
            <span className="blink font-mono text-[#ff4560] text-lg leading-none">|</span>
            <button
              onClick={stopRecording}
              className="font-mono text-sm uppercase tracking-widest border border-[#ff4560] text-[#ff4560] bg-transparent py-2 px-4 rounded-sm hover:bg-[#ff4560]/10 transition-colors ml-2"
            >
              stop
            </button>
          </div>
        )}

        {mode === "voice" && phase === "processing" && (
          <p className="font-mono text-sm text-[#445566] italic m-0">transcribing audio...</p>
        )}

        {/* Text mode entry (preserved logic; not in design spec) */}
        {mode === "text" && phase === "idle" && (
          <>
            <textarea
              value={typedAnswer}
              onChange={(e) => setTypedAnswer(e.target.value)}
              placeholder="Type your answer here…"
              rows={6}
              className="w-full bg-[#0d1520] border border-[#1e2d3d] rounded-sm p-3 font-mono text-sm text-[#e8edf3] resize-y placeholder:text-[#445566] focus:outline-none focus:border-[#00e5ff] transition-colors"
            />
            <div className="flex gap-3 flex-wrap mt-4">
              <button
                onClick={handleTextSubmitReview}
                disabled={typedAnswer.trim().length === 0}
                className={`${btnBase} border-[#00ff87] text-[#00ff87] ${
                  typedAnswer.trim().length === 0
                    ? "opacity-50 cursor-not-allowed"
                    : "hover:bg-[#00ff87]/10"
                }`}
              >
                review answer
              </button>
              <button
                onClick={handleHint}
                disabled={hintLoading}
                className={`${btnBase} border-[#ffb300] text-[#ffb300] ${
                  hintLoading ? "opacity-50 cursor-not-allowed" : "hover:bg-[#ffb300]/10"
                }`}
              >
                {hintLoading ? "…" : "get hint"}
              </button>
            </div>
          </>
        )}

        {(phase === "reviewing" || phase === "submitting") && (
          <>
            <div className="mb-4">
              <p className="font-mono text-xs text-[#445566] uppercase tracking-widest mb-2">
                your answer
              </p>
              <p className="font-mono text-sm text-[#8899aa] leading-relaxed border-l-2 border-[#1e2d3d] pl-3 m-0">
                {transcript || "(no speech detected)"}
              </p>
            </div>
            <div className="flex gap-3 flex-wrap mt-4">
              <button
                onClick={handleSubmit}
                disabled={phase === "submitting"}
                className={`${btnBase} border-[#00ff87] text-[#00ff87] ${
                  phase === "submitting"
                    ? "opacity-50 cursor-not-allowed"
                    : "hover:bg-[#00ff87]/10"
                }`}
              >
                {phase === "submitting" ? "scoring…" : "submit answer"}
              </button>
              <button
                onClick={handleHint}
                disabled={hintLoading}
                className={`${btnBase} border-[#ffb300] text-[#ffb300] ${
                  hintLoading ? "opacity-50 cursor-not-allowed" : "hover:bg-[#ffb300]/10"
                }`}
              >
                {hintLoading ? "…" : "get hint"}
              </button>
              <button
                onClick={() => {
                  setPhase("idle");
                  if (mode === "text") setTypedAnswer(transcript);
                }}
                className={`${btnBase} border-[#445566] text-[#445566] hover:bg-[#445566]/10`}
              >
                {mode === "voice" ? "re-record" : "edit answer"}
              </button>
            </div>
          </>
        )}

        {phase === "scored" && scores && (
          <>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <ScoreTile
                label="content"
                value={scores.content_score.toFixed(1)}
                suffix="/10"
                colorClass={scoreColorClass(scores.content_score)}
              />
              <ScoreTile
                label="delivery"
                value={scores.delivery_score.toFixed(1)}
                suffix="/10"
                colorClass={scoreColorClass(scores.delivery_score)}
              />
              <ScoreTile
                label="wpm"
                value={scores.wpm.toFixed(0)}
                suffix=""
                colorClass="text-[#8899aa]"
              />
              <ScoreTile
                label="fillers"
                value={(scores.filler_rate * 100).toFixed(1)}
                suffix="%"
                colorClass={scores.filler_rate > 0.1 ? "text-[#ff4560]" : "text-[#00ff87]"}
              />
            </div>

            <div className="mt-1">
              <span className="font-mono text-xs text-[#00e5ff] mr-2 select-none">&gt; </span>
              <span className="font-sans text-sm text-[#8899aa] leading-relaxed">
                {scores.feedback}
              </span>
            </div>

            {reportLoading && (
              <p className="font-mono text-xs text-[#445566] italic mt-3">generating report...</p>
            )}
            {!reportLoading && questionIndex < questions.length - 1 && (
              <button
                onClick={nextQuestion}
                className={`${btnBase} mt-4 w-full border-[#00e5ff] text-[#00e5ff] hover:bg-[#00e5ff]/10`}
              >
                next question →
              </button>
            )}
          </>
        )}

        {error && <p className="font-mono text-xs text-[#ff4560] mt-3">{error}</p>}
      </div>
    </div>
  );
}

function ScoreTile({
  label,
  value,
  suffix,
  colorClass,
}: {
  label: string;
  value: string;
  suffix: string;
  colorClass: string;
}) {
  return (
    <div className="bg-[#0d1520] border border-[#1e2d3d] rounded-sm p-3 text-center">
      <div>
        <span className={`font-mono text-3xl font-bold ${colorClass}`}>{value}</span>
        {suffix && <span className="font-mono text-xs text-[#445566] ml-0.5">{suffix}</span>}
      </div>
      <div className="font-mono text-xs text-[#445566] uppercase tracking-widest mt-1">
        {label}
      </div>
    </div>
  );
}

function Badge({ type, variant = "type" }: { type: string; variant?: "type" | "subtype" }) {
  const colors: Record<string, string> = {
    coding: "text-[#00e5ff]",
    behavioral: "text-[#00ff87]",
    system_design: "text-[#ffb300]",
    brain_teaser: "text-[#c084fc]",
    easy: "text-[#445566]",
    medium: "text-[#445566]",
    hard: "text-[#445566]",
  };
  const color = variant === "subtype" ? "text-[#445566]" : (colors[type] ?? "text-[#8899aa]");
  const label = type.replace(/_/g, " ");
  return <span className={`font-mono text-xs tracking-wide ${color}`}>[{label}]</span>;
}

function scoreColorClass(value: number): string {
  if (value >= 7) return "text-[#00ff87]";
  if (value >= 5) return "text-[#ffb300]";
  return "text-[#ff4560]";
}
