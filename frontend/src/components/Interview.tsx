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
    setScores(null);
    setHint(null);
    setError(null);
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>Interview</h2>
        <span style={{ color: "#64748b", fontSize: "0.9rem" }}>
          {questionIndex + 1} / {questions.length}
        </span>
      </div>

      {/* Progress bar */}
      <div style={{ height: 4, background: "#e2e8f0", borderRadius: 2, margin: "0.75rem 0" }}>
        <div
          style={{
            height: "100%",
            borderRadius: 2,
            background: "#2563eb",
            width: `${((questionIndex + (phase === "scored" ? 1 : 0)) / questions.length) * 100}%`,
            transition: "width 0.4s ease",
          }}
        />
      </div>

      {/* Question */}
      <div className="card">
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
          <Badge type={currentQuestion.type} />
          <Badge type={currentQuestion.difficulty} />
        </div>
        <p style={{ margin: 0, fontSize: "1.05rem", fontWeight: 500, lineHeight: 1.6 }}>
          {currentQuestion.text}
        </p>
      </div>

      {/* Hint */}
      {hint && (
        <div
          className="card"
          style={{ borderColor: "#fbbf24", background: "#fffbeb", marginTop: "0.75rem" }}
        >
          <strong style={{ color: "#92400e" }}>Hint</strong>
          <p style={{ margin: "0.25rem 0 0", color: "#78350f" }}>{hint}</p>
        </div>
      )}

      {/* Action area */}
      <div className="card" style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>

        {phase === "idle" && (
          <button onClick={startRecording} style={{ background: "#16a34a", fontSize: "1rem", padding: "0.75rem" }}>
            🎙 Start Recording
          </button>
        )}

        {phase === "recording" && (
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <span style={{ color: "#dc2626", fontWeight: 700, fontSize: "1rem" }}>
              ● Recording…
            </span>
            <button onClick={stopRecording} style={{ background: "#dc2626" }}>
              Stop
            </button>
          </div>
        )}

        {phase === "processing" && (
          <p style={{ color: "#64748b", margin: 0 }}>Transcribing audio…</p>
        )}

        {(phase === "reviewing" || phase === "submitting") && (
          <>
            <div>
              <strong>Your answer:</strong>
              <p style={{ margin: "0.4rem 0 0", color: "#475569", lineHeight: 1.6 }}>
                {transcript || "(no speech detected)"}
              </p>
            </div>
            <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
              <button onClick={handleSubmit} disabled={phase === "submitting"}>
                {phase === "submitting" ? "Scoring…" : "Submit Answer"}
              </button>
              <button
                onClick={handleHint}
                disabled={hintLoading}
                style={{ background: "#d97706" }}
              >
                {hintLoading ? "…" : "💡 Get Hint"}
              </button>
              <button onClick={() => setPhase("idle")} style={{ background: "#64748b" }}>
                Re-record
              </button>
            </div>
          </>
        )}

        {phase === "scored" && scores && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.5rem" }}>
              <ScoreTile label="Content" value={scores.content_score} suffix="/10" color={scoreColor(scores.content_score)} />
              <ScoreTile label="Delivery" value={scores.delivery_score} suffix="/10" color={scoreColor(scores.delivery_score)} />
              <ScoreTile label="WPM" value={scores.wpm} suffix="" decimals={0} color="#2563eb" />
              <ScoreTile label="Fillers" value={scores.filler_rate * 100} suffix="%" color={scores.filler_rate > 0.1 ? "#dc2626" : "#16a34a"} />
            </div>
            <div style={{ background: "#f1f5f9", borderRadius: 8, padding: "0.75rem" }}>
              <strong>Feedback</strong>
              <p style={{ margin: "0.3rem 0 0", color: "#475569", lineHeight: 1.6 }}>
                {scores.feedback}
              </p>
            </div>
            {reportLoading && <p style={{ color: "#64748b" }}>Generating report…</p>}
            {!reportLoading && questionIndex < questions.length - 1 && (
              <button onClick={nextQuestion}>Next Question →</button>
            )}
          </>
        )}

        {error && <p className="error" style={{ margin: 0 }}>{error}</p>}
      </div>
    </div>
  );
}

function ScoreTile({
  label,
  value,
  suffix,
  color,
  decimals = 1,
}: {
  label: string;
  value: number;
  suffix: string;
  color: string;
  decimals?: number;
}) {
  return (
    <div
      style={{
        textAlign: "center",
        background: "#f8fafc",
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        padding: "0.6rem 0.25rem",
      }}
    >
      <div style={{ fontSize: "1.5rem", fontWeight: 700, color }}>
        {value.toFixed(decimals)}
        <span style={{ fontSize: "0.8rem" }}>{suffix}</span>
      </div>
      <div style={{ fontSize: "0.7rem", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>
        {label}
      </div>
    </div>
  );
}

function Badge({ type }: { type: string }) {
  const palette: Record<string, { bg: string; color: string }> = {
    coding:        { bg: "#dbeafe", color: "#1e40af" },
    behavioral:    { bg: "#dcfce7", color: "#166534" },
    system_design: { bg: "#fef3c7", color: "#92400e" },
    technical:     { bg: "#ede9fe", color: "#5b21b6" },
    easy:          { bg: "#f0fdf4", color: "#15803d" },
    medium:        { bg: "#fff7ed", color: "#c2410c" },
    hard:          { bg: "#fef2f2", color: "#b91c1c" },
  };
  const { bg, color } = palette[type] ?? { bg: "#f1f5f9", color: "#475569" };
  return (
    <span
      style={{
        background: bg,
        color,
        padding: "0.15rem 0.6rem",
        borderRadius: 999,
        fontSize: "0.75rem",
        fontWeight: 600,
        textTransform: "capitalize",
      }}
    >
      {type.replace("_", " ")}
    </span>
  );
}

function scoreColor(value: number): string {
  if (value >= 7.5) return "#16a34a";
  if (value >= 5) return "#d97706";
  return "#dc2626";
}
