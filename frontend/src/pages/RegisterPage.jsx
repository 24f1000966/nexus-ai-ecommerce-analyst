import { ArrowLeft, ArrowRight, CheckCircle2, FileText, ImagePlus } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { errorMessage, registerCompany } from "../api";
import { Button, Field, inputClass } from "../components/ui";
import AuthLayout from "./AuthLayout";

const GSTIN_RE = /^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;
const PAN_RE = /^[A-Z]{5}\d{4}[A-Z]$/;
const CIN_RE = /^[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$/;
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const MAX_MB = 5;

const DATA_TYPES = [
  ["orders", "Orders & sales"], ["products", "Products & catalog"], ["customers", "Customers"],
  ["inventory", "Inventory & stock"], ["returns", "Returns & refunds"], ["marketing", "Marketing"],
];
const STEPS = ["Company", "Leadership & documents", "Data access & admin"];

const INITIAL = {
  company_name: "", website: "", address: "", cin: "", gstin: "", pan: "",
  md_name: "", md_email: "", logo: null, signatory_letter: null,
  data_types: [], data_purpose: "",
  admin_name: "", admin_designation: "Head of Finance", admin_email: "", admin_password: "", confirm_password: "",
};

function validate(step, f) {
  const e = {};
  if (step === 0) {
    if (!f.company_name.trim()) e.company_name = "Required";
    if (!f.website.trim()) e.website = "Required";
    if (!f.address.trim()) e.address = "Required";
    if (!CIN_RE.test(f.cin)) e.cin = "21 characters, e.g. U74999KA2015PTC123456";
    if (!GSTIN_RE.test(f.gstin)) e.gstin = "15 characters, e.g. 29ABCDE1234F1Z5";
    if (!PAN_RE.test(f.pan)) e.pan = "Format ABCDE1234F";
    else if (GSTIN_RE.test(f.gstin) && f.gstin.slice(2, 12) !== f.pan) e.pan = "PAN must match the PAN inside your GSTIN";
  }
  if (step === 1) {
    if (!f.md_name.trim()) e.md_name = "Required";
    if (f.md_email && !EMAIL_RE.test(f.md_email)) e.md_email = "Enter a valid email";
    if (!f.logo) e.logo = "Upload your company logo";
    if (!f.signatory_letter) e.signatory_letter = "Upload the signed authorization letter (PDF)";
  }
  if (step === 2) {
    if (!f.data_types.length) e.data_types = "Select at least one";
    if (!f.data_purpose.trim()) e.data_purpose = "Required";
    if (!f.admin_name.trim()) e.admin_name = "Required";
    if (!f.admin_designation.trim()) e.admin_designation = "Required";
    if (!EMAIL_RE.test(f.admin_email)) e.admin_email = "Enter a valid email";
    if (f.admin_password.length < 8) e.admin_password = "At least 8 characters";
    if (f.confirm_password !== f.admin_password) e.confirm_password = "Passwords do not match";
  }
  return e;
}

export default function RegisterPage() {
  const [step, setStep] = useState(0);
  const [f, setF] = useState(INITIAL);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));
  const setUpper = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value.toUpperCase().replace(/\s/g, "") }));
  const logoPreview = useMemo(() => (f.logo ? URL.createObjectURL(f.logo) : null), [f.logo]);

  function pickFile(k, allowed) {
    return (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const ext = "." + file.name.split(".").pop().toLowerCase();
      if (!allowed.includes(ext)) return setErrors((p) => ({ ...p, [k]: `Allowed: ${allowed.join(", ")}` }));
      if (file.size > MAX_MB * 1024 * 1024) return setErrors((p) => ({ ...p, [k]: `Must be under ${MAX_MB} MB` }));
      setErrors((p) => ({ ...p, [k]: undefined }));
      setF((p) => ({ ...p, [k]: file }));
    };
  }

  function next() {
    const e = validate(step, f);
    setErrors(e);
    if (!Object.keys(e).length) setStep((s) => s + 1);
  }

  async function submit(ev) {
    ev.preventDefault();
    const e = validate(2, f);
    setErrors(e);
    if (Object.keys(e).length) return;
    setBusy(true);
    setServerError("");
    const fd = new FormData();
    Object.entries(f).forEach(([k, v]) => {
      if (k === "confirm_password") return;
      fd.append(k, k === "data_types" ? v.join(",") : v);
    });
    try {
      await registerCompany(fd);
      setDone(true);
    } catch (err) {
      setServerError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <AuthLayout>
        <div className="text-center">
          <span className="mx-auto mb-4 grid place-items-center w-14 h-14 rounded-full bg-[var(--status-good-bg)] text-[var(--status-good)]"><CheckCircle2 size={28} /></span>
          <h2 className="text-2xl font-extrabold tracking-tight">Application submitted</h2>
          <p className="text-sm text-[var(--ink-secondary)] mt-2 leading-relaxed">
            Thanks! The Nexus AI team will verify <b>{f.company_name}</b> and grant access once approved.
            You can sign in any time with <b>{f.admin_email}</b> to track the status of your application.
          </p>
          <Link to="/login" className="mt-6 inline-block"><Button>Go to sign in</Button></Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout wide>
      <h2 className="text-2xl font-extrabold tracking-tight">Register your company</h2>
      <p className="text-sm text-[var(--ink-secondary)] mt-1 mb-6">
        We verify every organisation before granting access. Your details are seen only by the Nexus AI review team.
      </p>

      <ol className="flex items-center gap-2 mb-6">
        {STEPS.map((label, i) => (
          <li key={label} className="flex items-center gap-2 flex-1 min-w-0">
            <span className={`grid place-items-center w-7 h-7 rounded-full text-xs font-bold shrink-0 ${
              i < step ? "bg-[var(--status-good)] text-white" : i === step ? "bg-[var(--series-1)] text-white" : "bg-[var(--gridline)] text-[var(--ink-muted)]"}`}>
              {i < step ? "✓" : i + 1}
            </span>
            <span className={`text-[12.5px] font-semibold truncate ${i === step ? "text-[var(--ink-primary)]" : "text-[var(--ink-muted)]"}`}>{label}</span>
            {i < STEPS.length - 1 && <span className="flex-1 h-px bg-[var(--gridline)]" />}
          </li>
        ))}
      </ol>

      <form onSubmit={submit} className="rounded-2xl bg-white border border-[var(--border)] shadow-sm p-6 space-y-4">
        {step === 0 && (
          <>
            <Field label="Registered company name" error={errors.company_name}>
              <input className={inputClass} value={f.company_name} onChange={set("company_name")} placeholder="Meesho Private Limited" />
            </Field>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Company website" error={errors.website}>
                <input className={inputClass} value={f.website} onChange={set("website")} placeholder="https://www.meesho.com" />
              </Field>
              <Field label="PAN" error={errors.pan}>
                <input className={inputClass} value={f.pan} onChange={setUpper("pan")} maxLength={10} placeholder="ABCDE1234F" />
              </Field>
            </div>
            <Field label="Registered office address" error={errors.address}>
              <textarea className={inputClass} rows={2} value={f.address} onChange={set("address")} placeholder="Street, city, state, PIN" />
            </Field>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="CIN (Corporate Identity Number)" error={errors.cin} hint="From your MCA incorporation certificate">
                <input className={inputClass} value={f.cin} onChange={setUpper("cin")} maxLength={21} placeholder="U74999KA2015PTC123456" />
              </Field>
              <Field label="GSTIN" error={errors.gstin}>
                <input className={inputClass} value={f.gstin} onChange={setUpper("gstin")} maxLength={15} placeholder="29ABCDE1234F1Z5" />
              </Field>
            </div>
          </>
        )}

        {step === 1 && (
          <>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Managing Director / CEO name" error={errors.md_name}>
                <input className={inputClass} value={f.md_name} onChange={set("md_name")} placeholder="Full name" />
              </Field>
              <Field label="MD's official email (optional)" error={errors.md_email}>
                <input className={inputClass} type="email" value={f.md_email} onChange={set("md_email")} placeholder="md@company.com" />
              </Field>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Company logo" error={errors.logo} hint="PNG, JPG or WebP · max 5 MB">
                <label className="flex items-center gap-3 rounded-xl border border-dashed border-[var(--baseline)] bg-[var(--page)] p-3 cursor-pointer hover:border-[var(--series-1)] transition">
                  {logoPreview ? <img src={logoPreview} alt="" className="w-12 h-12 rounded-lg object-contain bg-white" /> :
                    <span className="grid place-items-center w-12 h-12 rounded-lg bg-white text-[var(--ink-muted)]"><ImagePlus size={20} /></span>}
                  <span className="text-sm text-[var(--ink-secondary)] truncate">{f.logo ? f.logo.name : "Choose image…"}</span>
                  <input type="file" accept=".png,.jpg,.jpeg,.webp" className="hidden" onChange={pickFile("logo", [".png", ".jpg", ".jpeg", ".webp"])} />
                </label>
              </Field>
              <Field label="Authorized signatory letter" error={errors.signatory_letter} hint="Signed PDF authorizing the applicant · max 5 MB">
                <label className="flex items-center gap-3 rounded-xl border border-dashed border-[var(--baseline)] bg-[var(--page)] p-3 cursor-pointer hover:border-[var(--series-1)] transition">
                  <span className="grid place-items-center w-12 h-12 rounded-lg bg-white text-[var(--ink-muted)]"><FileText size={20} /></span>
                  <span className="text-sm text-[var(--ink-secondary)] truncate">{f.signatory_letter ? f.signatory_letter.name : "Choose PDF…"}</span>
                  <input type="file" accept=".pdf" className="hidden" onChange={pickFile("signatory_letter", [".pdf"])} />
                </label>
              </Field>
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <Field label="Data you will upload to the platform" error={errors.data_types}>
              <div className="flex flex-wrap gap-2 mt-1">
                {DATA_TYPES.map(([key, label]) => {
                  const on = f.data_types.includes(key);
                  return (
                    <button type="button" key={key}
                      onClick={() => setF((p) => ({ ...p, data_types: on ? p.data_types.filter((t) => t !== key) : [...p.data_types, key] }))}
                      className={`rounded-full px-3.5 py-1.5 text-[13px] font-semibold border transition ${
                        on ? "bg-[var(--series-1)] text-white border-[var(--series-1)]" : "bg-white text-[var(--ink-secondary)] border-[var(--border)] hover:border-[var(--series-1)]"}`}>
                      {label}
                    </button>
                  );
                })}
              </div>
            </Field>
            <Field label="Why do you need this data analysed?" error={errors.data_purpose}>
              <textarea className={inputClass} rows={2} value={f.data_purpose} onChange={set("data_purpose")} placeholder="e.g. Monthly sales trends and stock planning for the leadership team" />
            </Field>
            <div className="pt-2 border-t border-[var(--border)]" />
            <p className="text-[12.5px] text-[var(--ink-secondary)]">
              This person becomes your <b>Company Admin</b> — typically the finance authority who uploads data and grants access to colleagues.
            </p>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Admin full name" error={errors.admin_name}>
                <input className={inputClass} value={f.admin_name} onChange={set("admin_name")} />
              </Field>
              <Field label="Designation" error={errors.admin_designation}>
                <input className={inputClass} value={f.admin_designation} onChange={set("admin_designation")} />
              </Field>
            </div>
            <Field label="Admin work email" error={errors.admin_email} hint="Use your company domain — free-mail addresses are flagged during review">
              <input className={inputClass} type="email" autoComplete="off" value={f.admin_email} onChange={set("admin_email")} placeholder="name@company.com" />
            </Field>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Password" error={errors.admin_password}>
                <input className={inputClass} type="password" autoComplete="new-password" value={f.admin_password} onChange={set("admin_password")} />
              </Field>
              <Field label="Confirm password" error={errors.confirm_password}>
                <input className={inputClass} type="password" autoComplete="new-password" value={f.confirm_password} onChange={set("confirm_password")} />
              </Field>
            </div>
          </>
        )}

        {serverError && <div className="rounded-xl bg-[var(--status-critical-bg)] text-[var(--status-critical)] text-sm px-3.5 py-2.5">{serverError}</div>}

        <div className="flex items-center justify-between pt-2">
          {step > 0 ? (
            <Button type="button" variant="ghost" onClick={() => setStep((s) => s - 1)}><ArrowLeft size={15} /> Back</Button>
          ) : (
            <Link to="/login" className="text-sm font-semibold text-[var(--ink-secondary)] hover:text-[var(--series-1)]">Already registered? Sign in</Link>
          )}
          {step < STEPS.length - 1 ? (
            <Button type="button" onClick={next}>Continue <ArrowRight size={15} /></Button>
          ) : (
            <Button type="submit" loading={busy}>Submit application</Button>
          )}
        </div>
      </form>
    </AuthLayout>
  );
}
