import type { ReportResponse } from "../api/client";

interface Props {
  report: ReportResponse;
  onRestart: () => void;
}

export default function Report({ report, onRestart }: Props) {
  return (
    <div>
      <h2 style={{ marginBottom: "0.25rem" }}>Session Complete</h2>
      <p style={{ color: "#64748b", marginTop: 0 }}>Here's how you did.</p>

      {/* Score overview */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem", marginBottom: "1rem" }}>
        <ScoreCard label="Content" value={report.avg_content_score} />
        <ScoreCard label="Delivery" value={report.avg_delivery_score} />
        <ScoreCard label="Overall" value={report.avg_overall} highlight />
      </div>

      {/* Summary */}
      <div className="card">
        <h3 style={{ margin: "0 0 0.5rem" }}>Summary</h3>
        <p style={{ margin: 0, color: "#475569", lineHeight: 1.7 }}>{report.summary}</p>
      </div>

      {/* Strengths */}
      <div className="card" style={{ borderColor: "#bbf7d0", background: "#f0fdf4" }}>
        <h3 style={{ margin: "0 0 0.5rem", color: "#166534" }}>Strengths</h3>
        <ul style={{ margin: 0, paddingLeft: "1.25rem", color: "#15803d", lineHeight: 1.8 }}>
          {report.strengths.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </div>

      {/* Areas to improve */}
      <div className="card" style={{ borderColor: "#fed7aa", background: "#fff7ed" }}>
        <h3 style={{ margin: "0 0 0.5rem", color: "#c2410c" }}>Areas to Improve</h3>
        <ul style={{ margin: 0, paddingLeft: "1.25rem", color: "#ea580c", lineHeight: 1.8 }}>
          {report.areas_to_improve.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ul>
      </div>

      {/* Next steps */}
      <div className="card">
        <h3 style={{ margin: "0 0 0.75rem" }}>Next Steps</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {report.next_steps.map((step, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                gap: "0.75rem",
                alignItems: "flex-start",
                background: "#f8fafc",
                borderRadius: 8,
                padding: "0.6rem 0.75rem",
              }}
            >
              <span
                style={{
                  background: "#2563eb",
                  color: "white",
                  borderRadius: "50%",
                  width: 22,
                  height: 22,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  flexShrink: 0,
                }}
              >
                {i + 1}
              </span>
              <span style={{ color: "#374151", lineHeight: 1.5 }}>{step}</span>
            </div>
          ))}
        </div>
      </div>

      <button onClick={onRestart} style={{ marginTop: "1rem", width: "100%", padding: "0.75rem", background: "#64748b" }}>
        Start New Session
      </button>
    </div>
  );
}

function ScoreCard({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  const color = value >= 7.5 ? "#16a34a" : value >= 5 ? "#d97706" : "#dc2626";
  return (
    <div
      className="card"
      style={{
        textAlign: "center",
        padding: "1rem",
        ...(highlight ? { borderColor: "#2563eb", background: "#eff6ff" } : {}),
      }}
    >
      <div style={{ fontSize: "2rem", fontWeight: 800, color }}>
        {value.toFixed(1)}
        <span style={{ fontSize: "1rem", color: "#94a3b8" }}>/10</span>
      </div>
      <div style={{ fontSize: "0.8rem", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginTop: "0.25rem" }}>
        {label}
      </div>
    </div>
  );
}
