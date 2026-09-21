import { AlertTriangle, ArrowUpRight } from "lucide-react";

export default function AnomalyBanner({ months, onExplain }) {
  return (
    <div
      className="animate-in flex items-center justify-between gap-4 rounded-2xl px-4 py-3"
      style={{
        background: "var(--status-critical-bg)",
        border: "1px solid rgba(208,59,59,0.22)",
        borderLeft: "4px solid var(--status-critical)",
      }}
    >
      <div className="flex items-center gap-3">
        <span className="grid place-items-center w-8 h-8 rounded-full bg-white/70 text-[var(--status-critical)] shrink-0">
          <AlertTriangle size={17} />
        </span>
        <p className="text-sm text-[var(--ink-primary)]">
          <b className="text-[var(--status-critical)]">Anomaly detected</b> — revenue dropped
          sharply in <b>{months.join(", ")}</b>. The agent already traced the root cause.
        </p>
      </div>
      <button
        onClick={onExplain}
        className="shrink-0 inline-flex items-center gap-1 rounded-xl bg-white px-3 py-2 text-sm font-semibold text-[var(--ink-primary)] border border-[var(--border)] hover:border-[var(--status-critical)] hover:text-[var(--status-critical)] transition-colors"
      >
        Explain this <ArrowUpRight size={15} />
      </button>
    </div>
  );
}
