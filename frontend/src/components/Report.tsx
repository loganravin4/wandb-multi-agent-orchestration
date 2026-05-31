import type { ReportResponse } from "../api/client";

interface Props {
  report: ReportResponse;
  onRestart: () => void;
}

export default function Report({ report, onRestart }: Props) {
  return (
    <div>
      {/* Header */}
      <p className="font-mono text-xs text-[#445566] mb-1 mt-0">// session complete</p>
      <p className="font-mono text-sm text-[#8899aa] mt-0 mb-8">here's how you did.</p>

      {/* Score grid */}
      <div className="grid grid-cols-3 gap-3 mb-8">
        <div className="bg-[#111822] border border-[#1e2d3d] rounded-sm p-4 text-center">
          <span className={`font-mono text-4xl font-bold ${scoreColorClass(report.avg_content_score)}`}>
            {report.avg_content_score.toFixed(1)}
          </span>
          <span className="font-mono text-sm text-[#445566] ml-1">/10</span>
          <span className="font-mono text-xs text-[#445566] uppercase tracking-widest mt-2 block">
            content
          </span>
        </div>
        <div className="bg-[#111822] border border-[#1e2d3d] rounded-sm p-4 text-center">
          <span className={`font-mono text-4xl font-bold ${scoreColorClass(report.avg_delivery_score)}`}>
            {report.avg_delivery_score.toFixed(1)}
          </span>
          <span className="font-mono text-sm text-[#445566] ml-1">/10</span>
          <span className="font-mono text-xs text-[#445566] uppercase tracking-widest mt-2 block">
            delivery
          </span>
        </div>
        <div className="bg-[#111822] border border-[#00e5ff] rounded-sm p-4 text-center">
          <span className={`font-mono text-4xl font-bold ${scoreColorClass(report.avg_overall)}`}>
            {report.avg_overall.toFixed(1)}
          </span>
          <span className="font-mono text-sm text-[#445566] ml-1">/10</span>
          <span className="font-mono text-xs text-[#445566] uppercase tracking-widest mt-2 block">
            overall
          </span>
        </div>
      </div>

      {/* Summary */}
      <div className="mb-6">
        <p className="font-mono text-xs text-[#445566] uppercase tracking-widest mb-2">## summary</p>
        <p className="font-sans text-sm text-[#8899aa] leading-relaxed m-0">{report.summary}</p>
      </div>

      {/* Strengths */}
      <div className="mb-6">
        <p className="font-mono text-xs text-[#445566] uppercase tracking-widest mb-3">## strengths</p>
        <div className="border-l-2 border-[#00ff87] pl-4 flex flex-col gap-2">
          {report.strengths.map((s, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="font-mono text-[#00ff87] select-none shrink-0">+</span>
              <span className="font-sans text-sm text-[#e8edf3]">{s}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Areas to improve */}
      <div className="mb-6">
        <p className="font-mono text-xs text-[#445566] uppercase tracking-widest mb-3">## areas to improve</p>
        <div className="border-l-2 border-[#ffb300] pl-4 flex flex-col gap-2">
          {report.areas_to_improve.map((a, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="font-mono text-[#ffb300] select-none shrink-0">~</span>
              <span className="font-sans text-sm text-[#e8edf3]">{a}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Next steps */}
      <div className="mb-8">
        <p className="font-mono text-xs text-[#445566] uppercase tracking-widest mb-3">## next steps</p>
        {report.next_steps.map((step, i) => (
          <div key={i} className="flex items-start gap-3 mb-3 last:mb-0">
            <span className="font-mono text-sm text-[#00e5ff] shrink-0 w-6">
              {String(i + 1).padStart(2, "0")}
            </span>
            <span className="font-sans text-sm text-[#e8edf3] leading-relaxed">{step}</span>
          </div>
        ))}
      </div>

      <button
        onClick={onRestart}
        className="w-full py-3 rounded-sm font-mono text-sm uppercase tracking-widest border border-[#1e2d3d] text-[#445566] bg-transparent hover:border-[#445566] hover:text-[#8899aa] transition-colors cursor-pointer"
      >
        start new session
      </button>
    </div>
  );
}

function scoreColorClass(value: number): string {
  if (value >= 7) return "text-[#00ff87]";
  if (value >= 5) return "text-[#ffb300]";
  return "text-[#ff4560]";
}
