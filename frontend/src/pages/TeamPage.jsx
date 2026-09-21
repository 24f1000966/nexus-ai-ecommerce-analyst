import { Crown, Eye, EyeOff, UserPlus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { addMember, errorMessage, getMembers, setMemberActive } from "../api";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, Field, inputClass } from "../components/ui";

const EMPTY = { full_name: "", designation: "", email: "", password: "" };
const SUGGESTED = ["Head of Operations", "Marketing Head", "Category Manager", "Supply Chain Lead", "CEO / MD"];

function generatePassword() {
  const chars = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789@#";
  const bytes = crypto.getRandomValues(new Uint32Array(12));
  return Array.from(bytes, (b) => chars[b % chars.length]).join("");
}

export default function TeamPage() {
  const { user } = useAuth();
  const [members, setMembers] = useState([]);
  const [form, setForm] = useState({ ...EMPTY, password: generatePassword() });
  const [showPw, setShowPw] = useState(true);
  const [created, setCreated] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => getMembers().then(setMembers).catch((e) => setError(errorMessage(e))), []);
  useEffect(() => { load(); }, [load]);

  const set = (k) => (e) => setForm((p) => ({ ...p, [k]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const m = await addMember(form);
      setCreated({ email: m.email, password: form.password, name: m.full_name });
      setForm({ ...EMPTY, password: generatePassword() });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function toggle(m) {
    try {
      await setMemberActive(m.id, !m.is_active);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="h-full overflow-y-auto px-6 py-6">
      <div className="max-w-5xl mx-auto grid lg:grid-cols-[1fr_360px] gap-6 items-start">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">Your team</h1>
          <p className="text-sm text-[var(--ink-secondary)] mt-1">
            People here can view {user.company.name}'s dashboards and ask the analyst questions. Only you can upload data or manage access.
          </p>

          <Card className="mt-5 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left bg-[var(--page)] text-[12px] text-[var(--ink-secondary)]">
                  <th className="px-4 py-2.5 font-semibold">Person</th>
                  <th className="px-4 py-2.5 font-semibold">Designation</th>
                  <th className="px-4 py-2.5 font-semibold">Access</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.id} className={`border-t border-[var(--border)] ${m.is_active ? "" : "opacity-50"}`}>
                    <td className="px-4 py-3">
                      <div className="font-semibold flex items-center gap-1.5">
                        {m.full_name}
                        {m.role === "company_admin" && <Crown size={13} className="text-[#b06b00]" title="Company admin" />}
                      </div>
                      <div className="text-[12px] text-[var(--ink-muted)]">{m.email}</div>
                    </td>
                    <td className="px-4 py-3 text-[var(--ink-secondary)]">{m.designation}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2.5 py-1 text-[11.5px] font-semibold ${
                        m.role === "company_admin" ? "bg-[#fdf1e0] text-[#b06b00]" : "bg-[var(--series-1)]/10 text-[var(--series-1)]"}`}>
                        {m.role === "company_admin" ? "Admin · full control" : "Viewer · insights"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {m.role !== "company_admin" && (
                        <button onClick={() => toggle(m)} className="text-[12.5px] font-semibold text-[var(--ink-secondary)] hover:text-[var(--series-1)]">
                          {m.is_active ? "Disable" : "Enable"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>

        <Card className="p-5">
          <h2 className="font-extrabold flex items-center gap-2"><UserPlus size={17} /> Add a team member</h2>
          <p className="text-[12.5px] text-[var(--ink-secondary)] mt-1 mb-4">They'll get view access to insights. Share the temporary password with them securely.</p>

          {created && (
            <div className="mb-4 rounded-xl bg-[var(--status-good-bg)] px-3.5 py-3 text-[12.5px]">
              <div className="font-semibold text-[#0a7a0a]">{created.name} added</div>
              <div className="mt-1 text-[var(--ink-secondary)]">Login: <b>{created.email}</b></div>
              <div className="text-[var(--ink-secondary)]">Temporary password: <b className="font-mono">{created.password}</b></div>
              <div className="mt-1 text-[var(--ink-muted)]">Shown once — copy it now.</div>
            </div>
          )}

          <form onSubmit={submit} className="space-y-3.5">
            <Field label="Full name"><input className={inputClass} value={form.full_name} onChange={set("full_name")} required /></Field>
            <Field label="Designation">
              <input className={inputClass} list="designations" value={form.designation} onChange={set("designation")} placeholder="e.g. Head of Operations" required />
              <datalist id="designations">{SUGGESTED.map((s) => <option key={s} value={s} />)}</datalist>
            </Field>
            <Field label="Work email"><input className={inputClass} type="email" value={form.email} onChange={set("email")} required /></Field>
            <Field label="Temporary password">
              <div className="relative">
                <input className={`${inputClass} pr-10 font-mono`} type={showPw ? "text" : "password"} value={form.password} onChange={set("password")} minLength={8} required />
                <button type="button" onClick={() => setShowPw((v) => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--ink-muted)]">
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </Field>
            {error && <div className="rounded-xl bg-[var(--status-critical-bg)] text-[var(--status-critical)] text-[13px] px-3.5 py-2.5">{error}</div>}
            <Button type="submit" loading={busy} className="w-full">Add member</Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
