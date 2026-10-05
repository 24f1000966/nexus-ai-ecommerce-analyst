import { AlertTriangle, BookOpen, CheckCircle2, Database, Download, FileText, Trash2, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  deleteDoc, deleteTable, downloadTemplate, errorMessage, getDataStatus, uploadDoc, uploadTable,
} from "../api";
import { Card } from "../components/ui";
import { useToast } from "../components/Toast";

const TABLE_LABEL = { customers: "Customers", products: "Products", orders: "Orders", order_items: "Order items" };
const fmtDate = (iso) => new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });

export default function DataPage() {
  const toast = useToast();
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(() => getDataStatus().then(setStatus).catch((e) => setError(errorMessage(e))), []);
  useEffect(() => { load(); }, [load]);

  async function run(key, fn, success) {
    setBusy(key);
    setError("");
    try {
      const s = await fn();
      setStatus(s);
      toast.success(success(s));
      (s.upload_warnings || []).forEach((w) => toast.info(w, 6000));
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy("");
    }
  }

  if (!status) {
    return <div className="h-full grid place-items-center text-sm text-[var(--ink-muted)]">{error || "Loading…"}</div>;
  }

  const uploadedCount = status.tables.filter((t) => t.uploaded).length;

  return (
    <div className="h-full overflow-y-auto px-6 py-6">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-2xl font-extrabold tracking-tight">Your data</h1>
        <p className="text-sm text-[var(--ink-secondary)] mt-1">
          Upload your store's CSV exports. Once all four tables are in, the analyst answers from your data only —
          nobody outside your company can query it.
        </p>

        <div
          className="mt-5 flex items-center gap-3 rounded-2xl px-4 py-3 text-sm"
          style={status.complete
            ? { background: "var(--status-good-bg)", color: "#0a7a0a" }
            : { background: "#fdf1e0", color: "#b06b00" }}
        >
          {status.complete ? <CheckCircle2 size={18} /> : <Database size={18} />}
          <span>
            {status.complete
              ? <><b>Analyst is using your uploaded data.</b> Re-upload any table to refresh it.</>
              : <><b>Analyst is using the demo dataset.</b> {uploadedCount} of 4 tables uploaded — upload the rest to switch to your data.</>}
          </span>
        </div>

        {error && <div className="mt-4 rounded-xl bg-[var(--status-critical-bg)] text-[var(--status-critical)] text-[13px] px-3.5 py-2.5">{error}</div>}
        {status.warnings.length > 0 && (
          <div className="mt-4 rounded-xl bg-[#fdf1e0] text-[#8a5400] text-[13px] px-3.5 py-2.5 space-y-1">
            {status.warnings.map((w) => <div key={w} className="flex gap-2"><AlertTriangle size={14} className="shrink-0 mt-0.5" /> {w}</div>)}
          </div>
        )}

        <div className="mt-5 grid md:grid-cols-2 gap-4">
          {status.tables.map((t) => (
            <TableCard
              key={t.table}
              t={t}
              busy={busy === t.table}
              onUpload={(file) => run(t.table, () => uploadTable(t.table, file), (s) => `${TABLE_LABEL[t.table]}: ${s.uploaded_rows.toLocaleString("en-IN")} rows uploaded.`)}
              onDelete={() => run(t.table, () => deleteTable(t.table), () => `${TABLE_LABEL[t.table]} removed.`)}
              onTemplate={() => downloadTemplate(t.table).catch((e) => setError(errorMessage(e)))}
            />
          ))}
        </div>

        <KnowledgeBase
          docs={status.docs}
          busy={busy === "doc"}
          onUpload={(file) => run("doc", () => uploadDoc(file), () => `${file.name} added to the knowledge base.`)}
          onDelete={(d) => run("doc", () => deleteDoc(d.id), () => `${d.title} removed.`)}
        />
      </div>
    </div>
  );
}

function FilePicker({ accept, busy, label, onPick, variant = "primary" }) {
  const ref = useRef(null);
  const styles = variant === "primary"
    ? "bg-[var(--series-1)] text-white hover:brightness-110"
    : "bg-white border border-[var(--border)] hover:bg-[var(--page)]";
  return (
    <>
      <input
        ref={ref}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) onPick(f); }}
      />
      <button
        type="button"
        disabled={busy}
        onClick={() => ref.current?.click()}
        className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold disabled:opacity-50 transition ${styles}`}
      >
        <Upload size={13} /> {busy ? "Uploading…" : label}
      </button>
    </>
  );
}

function useFileDrop(onFile, accept) {
  const [dragOver, setDragOver] = useState(false);

  function matches(file) {
    if (!accept) return true;
    const exts = accept.split(",").filter((a) => a.startsWith("."));
    return !exts.length || exts.some((ext) => file.name.toLowerCase().endsWith(ext));
  }

  return {
    dragOver,
    handlers: {
      onDragOver: (e) => { e.preventDefault(); setDragOver(true); },
      onDragLeave: () => setDragOver(false),
      onDrop: (e) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files?.[0];
        if (file && matches(file)) onFile(file);
      },
    },
  };
}

function TableCard({ t, busy, onUpload, onDelete, onTemplate }) {
  const { dragOver, handlers } = useFileDrop(onUpload, ".csv");

  return (
    <Card
      className={`relative p-4 transition-colors ${dragOver ? "ring-2 ring-[var(--series-1)] bg-[var(--series-1)]/5" : ""}`}
      {...handlers}
    >
      {dragOver && (
        <div className="absolute inset-0 z-10 grid place-items-center rounded-2xl bg-[var(--series-1)]/10 border-2 border-dashed border-[var(--series-1)] text-[var(--series-1)] text-sm font-semibold">
          Drop to upload {t.table}.csv
        </div>
      )}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-bold flex items-center gap-1.5">
            {TABLE_LABEL[t.table]}
            <span className="font-mono text-[11px] font-normal text-[var(--ink-muted)]">{t.table}.csv</span>
          </div>
          <div className="text-[12.5px] text-[var(--ink-secondary)] mt-0.5">{t.help}</div>
        </div>
        {t.uploaded
          ? <span className="shrink-0 rounded-full px-2.5 py-1 text-[11.5px] font-semibold bg-[var(--status-good-bg)] text-[#0a7a0a]">{t.rows.toLocaleString("en-IN")} rows</span>
          : <span className="shrink-0 rounded-full px-2.5 py-1 text-[11.5px] font-semibold bg-[var(--page)] text-[var(--ink-muted)]">Not uploaded</span>}
      </div>

      <div className="mt-3 flex flex-wrap gap-1">
        {t.columns.map((c) => (
          <code key={c} className="text-[11px] rounded bg-[var(--page)] px-1.5 py-0.5 text-[var(--ink-secondary)]">{c}</code>
        ))}
      </div>

      {t.uploaded && (
        <div className="mt-3 text-[11.5px] text-[var(--ink-muted)]">
          {t.filename} · {t.uploaded_by} · {fmtDate(t.uploaded_at)}
        </div>
      )}

      <div className="mt-3 flex items-center gap-2">
        <FilePicker accept=".csv,text/csv" busy={busy} label={t.uploaded ? "Replace" : "Upload CSV"} onPick={onUpload} />
        <span className="hidden sm:inline text-[11px] text-[var(--ink-muted)]">or drag & drop</span>
        <button onClick={onTemplate} className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold text-[var(--ink-secondary)] hover:bg-[var(--page)]">
          <Download size={13} /> Template
        </button>
        {t.uploaded && (
          <button onClick={onDelete} disabled={busy} className="ml-auto inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-[12.5px] font-semibold text-[var(--ink-muted)] hover:text-[var(--status-critical)] hover:bg-[var(--status-critical-bg)]">
            <Trash2 size={13} /> Remove
          </button>
        )}
      </div>
    </Card>
  );
}

function KnowledgeBase({ docs, busy, onUpload, onDelete }) {
  const { dragOver, handlers } = useFileDrop(onUpload, ".md,.txt");

  return (
    <Card className={`relative mt-6 p-5 transition-colors ${dragOver ? "ring-2 ring-[var(--series-1)] bg-[var(--series-1)]/5" : ""}`} {...handlers}>
      {dragOver && (
        <div className="absolute inset-0 z-10 grid place-items-center rounded-2xl bg-[var(--series-1)]/10 border-2 border-dashed border-[var(--series-1)] text-[var(--series-1)] text-sm font-semibold">
          Drop to add this document
        </div>
      )}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-extrabold flex items-center gap-2"><BookOpen size={17} /> Knowledge base (RAG)</h2>
          <p className="text-[12.5px] text-[var(--ink-secondary)] mt-1 max-w-2xl">
            Add your own policies, FAQs or SOPs as <b>.md</b> or <b>.txt</b> (or drag & drop one here). They are chunked
            by heading, indexed with TF-IDF, and retrieved alongside the platform's default policies.
          </p>
        </div>
        <FilePicker accept=".md,.txt,text/markdown,text/plain" busy={busy} label="Add document" onPick={onUpload} variant="ghost" />
      </div>
      {docs.length === 0 ? (
        <p className="mt-4 text-[13px] text-[var(--ink-muted)]">No company documents yet — the analyst uses the platform's default return, shipping and FAQ policies.</p>
      ) : (
        <ul className="mt-4 divide-y divide-[var(--border)]">
          {docs.map((d) => (
            <li key={d.id} className="flex items-center gap-3 py-2.5 text-sm">
              <FileText size={15} className="text-[var(--ink-muted)]" />
              <span className="font-semibold">{d.title}</span>
              <span className="text-[12px] text-[var(--ink-muted)]">{d.chars.toLocaleString("en-IN")} chars · {fmtDate(d.uploaded_at)}</span>
              <button onClick={() => onDelete(d)} disabled={busy} className="ml-auto text-[12.5px] font-semibold text-[var(--ink-muted)] hover:text-[var(--status-critical)]">
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
