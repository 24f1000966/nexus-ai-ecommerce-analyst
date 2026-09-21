import { BarChart3, ChevronDown, ListTree, TableIcon, User } from "lucide-react";
import { useState } from "react";
import { TrendLineChart, ValueBarChart } from "./Chart";
import DataTable from "./DataTable";
import Markdown from "./Markdown";

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
  const { answer, steps, table, chart, intent } = response;

  return (
    <div className="animate-in flex justify-start">
      <div className="max-w-[85%] w-full flex items-start gap-2.5">
        <span className="grid place-items-center w-8 h-8 rounded-full bg-[var(--series-1)] text-white shrink-0">
          <BarChart3 size={15} />
        </span>
        <div className="flex-1 min-w-0 rounded-2xl rounded-tl-sm bg-white border border-[var(--border)] px-4 py-3 shadow-sm">
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

          <p className="text-[14px] leading-relaxed text-[var(--ink-primary)]">
            <Markdown text={answer} />
          </p>

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
