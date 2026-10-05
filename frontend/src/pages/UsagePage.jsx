import { AlertTriangle, CheckCircle2, MessageCircle, RefreshCw, Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { errorMessage, getUsageLog } from "../api";
import { Button, Card } from "../components/ui";

const INTENT_LABEL = {
  top_products: "Top products", sales_trend: "Sales trend", category_revenue: "Category revenue",
  low_stock: "Low stock", avg_order_value: "Avg order value", sales_by_region: "Sales by region",
  top_customers: "Top customers", policy: "Policy (RAG)", why_drop: "Why drop (agentic)",
  anomaly: "Anomaly detection", general: "General", text_to_sql: "Text-to-SQL", unknown: "Unmatched", error: "Error",
};

const fmtDateTime = (iso) => new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });

export default function UsagePage() {
  const [rows, setRows] = useState(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setBusy(true);
    return getUsageLog(100)
      .then(setRows)
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setBusy(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const visible = useMemo(() => {
    if (!rows) return [];
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => [r.company, r.user, r.question].some((v) => v?.toLowerCase().includes(q)));
  }, [rows, search]);

  return (
    <div className="h-full overflow-y-auto px-6 py-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight">Usage log</h1>
            <p className="text-sm text-[var(--ink-secondary)] mt-1">
              The most recent questions asked across every company — what people actually use the analyst for.
            </p>
          </div>
          <Button variant="ghost" onClick={load} loading={busy}><RefreshCw size={14} /> Refresh</Button>
        </div>

        <div className="relative mt-5 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ink-muted)]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search company, user or question…"
            className="w-full rounded-xl border border-[var(--border)] bg-white pl-8 pr-3 py-2.5 text-[13px] outline-none focus:border-[var(--series-1)] transition-colors"
          />
        </div>

        {error && <div className="mt-4 rounded-xl bg-[var(--status-critical-bg)] text-[var(--status-critical)] text-sm px-3.5 py-2.5">{error}</div>}

        <Card className="mt-4 overflow-hidden">
          {!rows ? (
            <div className="py-16 text-center text-sm text-[var(--ink-muted)]">Loading…</div>
          ) : visible.length === 0 ? (
            <div className="py-16 text-center text-sm text-[var(--ink-muted)]">
              {rows.length === 0 ? (
                <>
                  <MessageCircle size={22} className="mx-auto mb-2 text-[var(--ink-muted)]" />
                  No questions have been asked yet.
                </>
              ) : "No questions match your search."}
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left bg-[var(--page)] text-[12px] text-[var(--ink-secondary)]">
                  <th className="px-4 py-2.5 font-semibold">When</th>
                  <th className="px-4 py-2.5 font-semibold">Company</th>
                  <th className="px-4 py-2.5 font-semibold">Asked by</th>
                  <th className="px-4 py-2.5 font-semibold">Question</th>
                  <th className="px-4 py-2.5 font-semibold">Intent</th>
                  <th className="px-4 py-2.5 font-semibold w-8" />
                </tr>
              </thead>
              <tbody>
                {visible.map((r, i) => (
                  <tr key={i} className="border-t border-[var(--border)]">
                    <td className="px-4 py-3 text-[var(--ink-muted)] text-[12.5px] whitespace-nowrap tabular-nums">{fmtDateTime(r.at)}</td>
                    <td className="px-4 py-3 font-semibold">{r.company}</td>
                    <td className="px-4 py-3 text-[var(--ink-secondary)]">{r.user}</td>
                    <td className="px-4 py-3 text-[var(--ink-primary)] max-w-xs truncate" title={r.question}>{r.question}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-[var(--series-1)]/10 text-[var(--series-1)] px-2.5 py-1 text-[11.5px] font-semibold whitespace-nowrap">
                        {INTENT_LABEL[r.intent] || r.intent}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {r.ok
                        ? <CheckCircle2 size={15} className="text-[var(--status-good)]" title="Answered successfully" />
                        : <AlertTriangle size={15} className="text-[var(--status-critical)]" title="The agent raised an error" />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}
