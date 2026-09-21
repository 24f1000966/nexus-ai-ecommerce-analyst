import { CheckCircle2, ExternalLink, FileText, Globe, Mail, MapPin, ShieldAlert, X, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { decideCompany, errorMessage, getAdminCompanies, getAdminStats, getCompanyReview, openLetter } from "../api";
import { Button, Card, CompanyLogo, StatusPill } from "../components/ui";

const FILTERS = [["pending", "Pending"], ["approved", "Approved"], ["rejected", "Rejected"], ["suspended", "Suspended"], ["", "All"]];
const fmtDate = (iso) => new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

export default function AdminPage() {
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState("pending");
  const [companies, setCompanies] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [s, c] = await Promise.all([getAdminStats(), getAdminCompanies(filter)]);
      setStats(s);
      setCompanies(c);
    } catch (e) {
      setError(errorMessage(e));
    }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const cards = [
    ["pending", "Awaiting review", "#b06b00"], ["approved", "Approved companies", "var(--status-good)"],
    ["rejected", "Rejected", "var(--status-critical)"], ["suspended", "Suspended", "var(--ink-secondary)"],
  ];

  return (
    <div className="h-full overflow-y-auto px-6 py-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl font-extrabold tracking-tight">Company verification</h1>
        <p className="text-sm text-[var(--ink-secondary)] mt-1">Review applications, verify documents, and control which companies can use Nexus AI.</p>

        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-5">
            {cards.map(([key, label, color]) => (
              <button key={key} onClick={() => setFilter(key)} className="text-left">
                <Card className={`p-4 hover:shadow-md transition ${filter === key ? "ring-2 ring-[var(--series-1)]/40" : ""}`}>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--ink-muted)]">{label}</div>
                  <div className="text-3xl font-extrabold mt-1 tabular-nums" style={{ color }}>{stats[key]}</div>
                </Card>
              </button>
            ))}
            <Card className="p-4">
              <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--ink-muted)]">Platform users</div>
              <div className="text-3xl font-extrabold mt-1 tabular-nums">{stats.users}</div>
            </Card>
          </div>
        )}

        <div className="flex gap-1 mt-6 mb-3 rounded-xl bg-white border border-[var(--border)] p-1 w-fit">
          {FILTERS.map(([key, label]) => (
            <button key={label} onClick={() => setFilter(key)}
              className={`rounded-lg px-3.5 py-1.5 text-[13px] font-semibold transition ${filter === key ? "bg-[var(--series-1)] text-white" : "text-[var(--ink-secondary)] hover:bg-[var(--page)]"}`}>
              {label}
            </button>
          ))}
        </div>

        {error && <div className="mb-3 rounded-xl bg-[var(--status-critical-bg)] text-[var(--status-critical)] text-sm px-3.5 py-2.5">{error}</div>}

        <Card className="overflow-hidden">
          {companies.length === 0 ? (
            <div className="py-16 text-center text-sm text-[var(--ink-muted)]">No companies in this view.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left bg-[var(--page)] text-[12px] text-[var(--ink-secondary)]">
                  <th className="px-4 py-2.5 font-semibold">Company</th>
                  <th className="px-4 py-2.5 font-semibold">Applicant</th>
                  <th className="px-4 py-2.5 font-semibold">MD</th>
                  <th className="px-4 py-2.5 font-semibold">Submitted</th>
                  <th className="px-4 py-2.5 font-semibold">Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {companies.map((c) => (
                  <tr key={c.id} className="border-t border-[var(--border)] hover:bg-[var(--page)]/60 cursor-pointer" onClick={() => setSelected(c.id)}>
                    <td className="px-4 py-3"><div className="flex items-center gap-3"><CompanyLogo company={c} size={34} /><span className="font-semibold">{c.name}</span></div></td>
                    <td className="px-4 py-3 text-[var(--ink-secondary)]">{c.applicant}</td>
                    <td className="px-4 py-3 text-[var(--ink-secondary)]">{c.md_name}</td>
                    <td className="px-4 py-3 text-[var(--ink-secondary)] tabular-nums">{fmtDate(c.created_at)}</td>
                    <td className="px-4 py-3"><StatusPill status={c.status} /></td>
                    <td className="px-4 py-3 text-right"><span className="text-[13px] font-semibold text-[var(--series-1)]">Review →</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      {selected && <ReviewDrawer id={selected} onClose={() => setSelected(null)} onChanged={load} />}
    </div>
  );
}

function ReviewDrawer({ id, onClose, onChanged }) {
  const [data, setData] = useState(null);
  const [mode, setMode] = useState(null); // "reject" | "suspend"
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => getCompanyReview(id).then(setData).catch((e) => setError(errorMessage(e))), [id]);
  useEffect(() => { load(); }, [load]);

  async function decide(action) {
    setBusy(true);
    setError("");
    try {
      await decideCompany(id, action, reason);
      setMode(null);
      setReason("");
      await Promise.all([load(), onChanged()]);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const c = data?.company;
  const passed = data?.checks.filter((k) => k.passed).length ?? 0;

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <aside className="relative w-full max-w-xl h-full bg-[var(--surface)] shadow-2xl overflow-y-auto animate-in">
        <div className="sticky top-0 z-10 flex items-center justify-between px-6 py-4 bg-[var(--surface)] border-b border-[var(--border)]">
          <span className="text-sm font-semibold text-[var(--ink-muted)]">Application review</span>
          <button onClick={onClose} className="grid place-items-center w-8 h-8 rounded-lg hover:bg-[var(--page)]"><X size={17} /></button>
        </div>

        {!data ? (
          <div className="p-8 text-sm text-[var(--ink-muted)]">{error || "Loading…"}</div>
        ) : (
          <div className="p-6 space-y-6">
            <div className="flex items-center gap-4">
              <CompanyLogo company={c} size={64} />
              <div className="min-w-0">
                <h2 className="text-xl font-extrabold tracking-tight truncate">{c.name}</h2>
                <div className="mt-1"><StatusPill status={c.status} /></div>
              </div>
            </div>

            <Section title={`Verification checks · ${passed}/${data.checks.length} passed`}>
              <ul className="space-y-2">
                {data.checks.map((k) => (
                  <li key={k.key} className="flex items-start gap-2.5 text-[13px]">
                    {k.passed ? <CheckCircle2 size={17} className="text-[var(--status-good)] shrink-0 mt-px" /> : <ShieldAlert size={17} className="text-[var(--status-critical)] shrink-0 mt-px" />}
                    <div>
                      <div className="font-semibold">{k.label}</div>
                      <div className="text-[12px] text-[var(--ink-muted)] font-mono">{k.detail}</div>
                    </div>
                  </li>
                ))}
              </ul>
              <p className="text-[11.5px] text-[var(--ink-muted)] mt-3">Automated checks flag obvious problems only — always review the letter yourself.</p>
            </Section>

            <Section title="Company details">
              <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-[13px]">
                <Detail label="CIN" value={c.cin} mono /><Detail label="GSTIN" value={c.gstin} mono />
                <Detail label="PAN" value={c.pan} mono />
                <Detail label="Website" value={c.website} icon={Globe} />
                <div className="col-span-2"><Detail label="Registered address" value={c.address} icon={MapPin} /></div>
              </dl>
            </Section>

            <Section title="Leadership & applicant">
              <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-[13px]">
                <Detail label="Managing Director" value={c.md_name} />
                <Detail label="MD email" value={c.md_email || "—"} icon={Mail} />
                <Detail label="Applicant (Company Admin)" value={`${data.applicant.full_name} · ${data.applicant.designation}`} />
                <Detail label="Applicant email" value={data.applicant.email} icon={Mail} />
              </dl>
              {c.has_letter && (
                <Button variant="ghost" className="mt-4" onClick={() => openLetter(id)}>
                  <FileText size={15} /> View authorization letter <ExternalLink size={13} />
                </Button>
              )}
            </Section>

            <Section title="Data access declaration">
              <div className="flex flex-wrap gap-1.5">
                {c.data_types.map((t) => (
                  <span key={t} className="rounded-full bg-[var(--series-1)]/10 text-[var(--series-1)] px-3 py-1 text-[12px] font-semibold capitalize">{t}</span>
                ))}
              </div>
              <p className="text-[13px] text-[var(--ink-secondary)] mt-3 leading-relaxed">“{c.data_purpose}”</p>
            </Section>

            {(c.status_note && c.status !== "approved") && (
              <Section title="Last decision note"><p className="text-[13px] text-[var(--ink-secondary)]">{c.status_note}</p></Section>
            )}

            <Section title="Activity">
              <ul className="space-y-2">
                {data.audit.map((a, i) => (
                  <li key={i} className="text-[12.5px] text-[var(--ink-secondary)]">
                    <b className="capitalize">{a.action.replace(/_/g, " ")}</b> by {a.actor}
                    <span className="text-[var(--ink-muted)]"> · {fmtDate(a.at)}</span>
                    {a.note && a.action !== "submitted" && <div className="text-[var(--ink-muted)]">“{a.note}”</div>}
                  </li>
                ))}
              </ul>
            </Section>

            {error && <div className="rounded-xl bg-[var(--status-critical-bg)] text-[var(--status-critical)] text-sm px-3.5 py-2.5">{error}</div>}

            {mode ? (
              <div className="rounded-2xl border border-[var(--border)] bg-white p-4 space-y-3">
                <div className="text-sm font-semibold capitalize">{mode} — give a reason (shown to the company)</div>
                <textarea autoFocus rows={3} value={reason} onChange={(e) => setReason(e.target.value)}
                  className="w-full rounded-xl border border-[var(--border)] px-3.5 py-2.5 text-sm outline-none focus:border-[var(--series-1)]"
                  placeholder={mode === "reject" ? "e.g. GSTIN does not match the company name on the letter" : "e.g. Requested by the company"} />
                <div className="flex gap-2">
                  <Button variant="danger" loading={busy} disabled={!reason.trim()} onClick={() => decide(mode)}>Confirm {mode}</Button>
                  <Button variant="ghost" onClick={() => { setMode(null); setReason(""); }}>Cancel</Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2 pb-4">
                {["pending", "rejected", "suspended"].includes(c.status) && (
                  <Button variant="success" loading={busy} onClick={() => decide("approve")}>
                    <CheckCircle2 size={16} /> {c.status === "pending" ? "Approve & grant access" : "Re-approve"}
                  </Button>
                )}
                {c.status === "pending" && <Button variant="ghost" onClick={() => setMode("reject")}><XCircle size={16} /> Reject</Button>}
                {c.status === "approved" && <Button variant="ghost" onClick={() => setMode("suspend")}>Suspend access</Button>}
              </div>
            )}
          </div>
        )}
      </aside>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section>
      <h3 className="text-[11px] font-bold uppercase tracking-wide text-[var(--ink-muted)] mb-2.5">{title}</h3>
      {children}
    </section>
  );
}

function Detail({ label, value, mono, icon: Icon }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11.5px] text-[var(--ink-muted)] flex items-center gap-1">{Icon && <Icon size={11} />}{label}</dt>
      <dd className={`font-semibold break-words ${mono ? "font-mono text-[12.5px]" : ""}`}>{value}</dd>
    </div>
  );
}
