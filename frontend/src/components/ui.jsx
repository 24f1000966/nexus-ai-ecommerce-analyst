import { Loader2 } from "lucide-react";

export function Field({ label, hint, error, children }) {
  return (
    <label className="block">
      <span className="block text-[12.5px] font-semibold text-[var(--ink-secondary)] mb-1">{label}</span>
      {children}
      {error ? (
        <span className="block mt-1 text-[11.5px] text-[var(--status-critical)]">{error}</span>
      ) : hint ? (
        <span className="block mt-1 text-[11.5px] text-[var(--ink-muted)]">{hint}</span>
      ) : null}
    </label>
  );
}

export const inputClass =
  "w-full rounded-xl border border-[var(--border)] bg-white px-3.5 py-2.5 text-[14px] outline-none placeholder:text-[var(--ink-muted)] focus:border-[var(--series-1)] focus:ring-4 focus:ring-[var(--series-1)]/10 transition";

export function Button({ children, loading, variant = "primary", className = "", ...props }) {
  const styles = {
    primary: "bg-[var(--series-1)] text-white hover:brightness-110",
    ghost: "bg-white text-[var(--ink-primary)] border border-[var(--border)] hover:bg-[var(--page)]",
    danger: "bg-[var(--status-critical)] text-white hover:brightness-110",
    success: "bg-[var(--status-good)] text-white hover:brightness-110",
  }[variant];
  return (
    <button
      {...props}
      disabled={loading || props.disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition ${styles} ${className}`}
    >
      {loading && <Loader2 size={15} className="animate-spin" />}
      {children}
    </button>
  );
}

const STATUS_STYLES = {
  pending: { bg: "#fdf1e0", fg: "#b06b00", label: "Pending review" },
  approved: { bg: "var(--status-good-bg)", fg: "#0a7a0a", label: "Approved" },
  rejected: { bg: "var(--status-critical-bg)", fg: "var(--status-critical)", label: "Rejected" },
  suspended: { bg: "#ececea", fg: "#52514e", label: "Suspended" },
};

export function StatusPill({ status }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.pending;
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11.5px] font-semibold" style={{ background: s.bg, color: s.fg }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: s.fg }} />
      {s.label}
    </span>
  );
}

export function CompanyLogo({ company, size = 40 }) {
  return company?.logo_url ? (
    <img src={company.logo_url} alt="" style={{ width: size, height: size }} className="rounded-xl object-contain bg-white border border-[var(--border)] shrink-0" />
  ) : (
    <span style={{ width: size, height: size }} className="grid place-items-center rounded-xl bg-[var(--series-1)]/10 text-[var(--series-1)] font-bold shrink-0">
      {company?.name?.[0] ?? "?"}
    </span>
  );
}

export function Card({ children, className = "" }) {
  return <div className={`rounded-2xl bg-white border border-[var(--border)] shadow-sm ${className}`}>{children}</div>;
}
