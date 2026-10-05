import { BarChart3, BookOpen, Check, ChevronDown, Code2, Copy, ListTree, TableIcon, User } from "lucide-react";
import { useState } from "react";
import { TrendLineChart, ValueBarChart } from "./Chart";
import DataTable from "./DataTable";
import Markdown from "./Markdown";

function plainText(markdown) {
  return markdown.replace(/\*\*([^*]+)\*\*/g, "$1").replace(/\*([^*]+)\*/g, "$1").replace(/^>\s?/gm, "");
}

export function UserBubble({ text }) {
  return (
    <div className="animate-in flex justify-end">
      <div className="max-w-[75%] flex items-start gap-2.5">
        <div className="rounded-2xl rounded-tr-sm bg-[var(--series-1)] text-white px-4 py-2.5 text-[14px] leading-snug shadow-sm">
          {text}
        </div>
        <span className="grid place-items-center w-8 h-8 rounded-full bg-[var(--series-1)]/10 text-[var(--series-1)] shrink-0">
          <User size={15} />
        </span>
      </div>
    </div>
  );
}

export function AssistantBubble({ response }) {
  const [traceOpen, setTraceOpen] = useState(false);
  const [tab, setTab] = useState("chart");
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const { answer, steps, table, chart, intent, sources, sql } = response;

  async function copyAnswer() {
    try {
      await navigator.clipboard.writeText(plainText(answer));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable — silently ignore
    }
  }

  return (
    <div className="animate-in group flex justify-start">
      <div className="max-w-[85%] w-full flex items-start gap-2.5">
        <span className="grid place-items-center w-8 h-8 rounded-full bg-[var(--series-1)] text-white shrink-0">
          <BarChart3 size={15} />
        </span>
        <div className="relative flex-1 min-w-0 rounded-2xl rounded-tl-sm bg-white border border-[var(--border)] px-4 py-3 shadow-sm">
          <button
            onClick={copyAnswer}
            title="Copy answer"
            className="absolute top-2.5 right-2.5 grid place-items-center w-6 h-6 rounded-md text-[var(--ink-muted)] opacity-0 group-hover:opacity-100 hover:bg-[var(--page)] hover:text-[var(--series-1)] transition-all"
          >
            {copied ? <Check size={13} className="text-[var(--status-good)]" /> : <Copy size={13} />}
          </button>

          {steps?.length > 0 && (
            <button
              onClick={() => setTraceOpen((v) => !v)}
              className="mb-2 flex items-center gap-1.5 text-[11.5px] font-semibold text-[var(--ink-muted)] hover:text-[var(--series-1)]"
            >
              <ListTree size={13} />
              Reasoning trace ({steps.length} step{steps.length > 1 ? "s" : ""})
              <ChevronDown size={12} className={`transition-transform ${traceOpen ? "rotate-180" : ""}`} />
            </button>
          )}
          {traceOpen && (
            <ol className="mb-3 pl-4 border-l-2 border-[var(--gridline)] space-y-1.5">
              {steps.map((s, i) => (
                <li key={i} className="text-[12px] text-[var(--ink-secondary)] pl-2 -ml-[9px] relative">
                  <span className="absolute -left-[13px] top-1 w-2 h-2 rounded-full bg-[var(--series-1)]" />
                  {s}
                </li>
              ))}
            </ol>
          )}

          <div className="text-[14px] leading-relaxed text-[var(--ink-primary)]">
            <Markdown text={answer} />
          </div>

          {sources?.length > 0 && (
            <div className="mt-3">
              <button
                onClick={() => setSourcesOpen((v) => !v)}
                className="flex items-center gap-1.5 text-[11.5px] font-semibold text-[var(--ink-muted)] hover:text-[var(--series-1)]"
              >
                <BookOpen size={13} />
                {sources.length} source{sources.length > 1 ? "s" : ""} retrieved (RAG)
                <ChevronDown size={12} className={`transition-transform ${sourcesOpen ? "rotate-180" : ""}`} />
              </button>
              {sourcesOpen && (
                <ul className="mt-2 space-y-2">
                  {sources.map((s, i) => (
                    <li key={i} className="rounded-lg bg-[var(--page)] px-3 py-2">
                      <div className="flex items-center justify-between gap-3 text-[11.5px] font-semibold text-[var(--ink-secondary)]">
                        <span>[{i + 1}] {s.doc.replace(/^\d+:/, "")}{s.section ? ` › ${s.section}` : ""}</span>
                        <span className="tabular-nums text-[var(--ink-muted)]" title="Cosine similarity">score {s.score.toFixed(2)}</span>
                      </div>
                      <p className="mt-1 text-[12px] leading-snug text-[var(--ink-secondary)] line-clamp-3">{s.text}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {sql && (
            <pre className="mt-3 flex gap-2 text-[11.5px] leading-relaxed bg-[var(--page)] rounded-lg p-2.5 overflow-x-auto text-[var(--ink-secondary)]">
              <Code2 size={13} className="shrink-0 mt-0.5" />
              {sql}
            </pre>
          )}

          {table?.length > 0 && (
            <div className="mt-3">
              {chart && (
                <div className="flex gap-1 mb-2.5 rounded-lg bg-[var(--page)] p-1 w-fit">
                  <TabButton active={tab === "chart"} onClick={() => setTab("chart")} icon={BarChart3} label="Chart" />
                  <TabButton active={tab === "table"} onClick={() => setTab("table")} icon={TableIcon} label="Table" />
                </div>
              )}
              {(!chart || tab === "chart") && chart && (
                chart.type === "line" ? (
                  <TrendLineChart data={table} xKey={chart.x} yKey={chart.y} />
                ) : (
                  <ValueBarChart data={table} xKey={chart.x} yKey={chart.y} highlightNegative={intent === "why_drop"} />
                )
              )}
              {(tab === "table" || !chart) && <DataTable rows={table} />}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function TabButton({ active, onClick, icon: Icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-semibold transition-colors ${
        active ? "bg-white text-[var(--series-1)] shadow-sm" : "text-[var(--ink-muted)] hover:text-[var(--ink-secondary)]"
      }`}
    >
      <Icon size={13} /> {label}
    </button>
  );
}
