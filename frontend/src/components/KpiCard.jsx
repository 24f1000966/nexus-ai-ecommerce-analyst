export default function KpiCard({ icon: Icon, label, value, sub, accent = "var(--series-1)" }) {
  return (
    <div className="rounded-2xl bg-white border border-[var(--border)] p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
          {label}
        </span>
        {Icon && (
          <span
            className="grid place-items-center w-8 h-8 rounded-lg"
            style={{ background: `${accent}1a`, color: accent }}
          >
            <Icon size={16} strokeWidth={2.25} />
          </span>
        )}
      </div>
      <div className="mt-2 text-2xl font-extrabold tabular-nums text-[var(--ink-primary)]">
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-[var(--ink-secondary)]">{sub}</div>}
    </div>
  );
}
