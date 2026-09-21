import { CheckCircle2, Circle, Clock, RefreshCw, XCircle } from "lucide-react";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, CompanyLogo, StatusPill } from "../components/ui";

export default function StatusPage() {
  const { user, refresh } = useAuth();
  const [busy, setBusy] = useState(false);
  const company = user.company;

  if (user.role === "super_admin") return <Navigate to="/admin" replace />;
  if (company?.status === "approved") return <Navigate to="/dashboard" replace />;

  const status = company?.status;
  const bad = status === "rejected" || status === "suspended";

  async function check() {
    setBusy(true);
    try { await refresh(); } finally { setBusy(false); }
  }

  return (
    <div className="h-full overflow-y-auto grid place-items-center px-5 py-10">
      <Card className="w-full max-w-xl p-8">
        <div className="flex items-center gap-3 mb-6">
          <CompanyLogo company={company} size={48} />
          <div className="flex-1 min-w-0">
            <div className="font-extrabold text-lg truncate">{company.name}</div>
            <StatusPill status={status} />
          </div>
        </div>

        {!bad && (
          <>
            <h2 className="text-xl font-extrabold tracking-tight">Your application is under review</h2>
            <p className="text-sm text-[var(--ink-secondary)] mt-1.5 leading-relaxed">
              The Nexus AI team is verifying your company details and documents. You'll get access to the
              platform as soon as it's approved — check back here any time.
            </p>
            <ol className="mt-6 space-y-4">
              <Step done label="Application submitted" text="We received your company details and documents." />
              <Step active label="Verification in progress" text="Our team is checking your GSTIN, PAN, CIN and signatory letter." />
              <Step label="Access granted" text="Your admin account unlocks the dashboard, data upload and team management." />
            </ol>
          </>
        )}

        {bad && (
          <>
            <div className="flex items-center gap-2 text-[var(--status-critical)]">
              <XCircle size={20} />
              <h2 className="text-xl font-extrabold tracking-tight">
                {status === "rejected" ? "Application not approved" : "Access suspended"}
              </h2>
            </div>
            <p className="text-sm text-[var(--ink-secondary)] mt-2">Reason given by the review team:</p>
            <blockquote className="mt-2 rounded-xl bg-[var(--status-critical-bg)] px-4 py-3 text-sm text-[var(--ink-primary)]">
              {company.status_note || "No reason was provided."}
            </blockquote>
            <p className="text-xs text-[var(--ink-muted)] mt-3">Contact the Nexus AI team if you believe this is a mistake.</p>
          </>
        )}

        <Button variant="ghost" onClick={check} loading={busy} className="mt-7"><RefreshCw size={14} /> Refresh status</Button>
      </Card>
    </div>
  );
}

function Step({ done, active, label, text }) {
  const Icon = done ? CheckCircle2 : active ? Clock : Circle;
  const color = done ? "var(--status-good)" : active ? "var(--series-1)" : "var(--baseline)";
  return (
    <li className="flex gap-3">
      <Icon size={20} style={{ color }} className="shrink-0 mt-0.5" />
      <div>
        <div className={`text-sm font-semibold ${!done && !active ? "text-[var(--ink-muted)]" : ""}`}>{label}</div>
        <div className="text-[13px] text-[var(--ink-secondary)]">{text}</div>
      </div>
    </li>
  );
}
