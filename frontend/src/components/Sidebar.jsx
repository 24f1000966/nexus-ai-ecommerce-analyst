import {
  BarChart3, Bot, ChevronDown, Database, FileText,
  Package, Sparkles, Trash2, TrendingUp, Users,
} from "lucide-react";
import { useState } from "react";

const GROUP_ICONS = {
  Sales: TrendingUp,
  Inventory: Package,
  Customers: Users,
  "Policy (RAG)": FileText,
  "Agentic / Autonomous": Bot,
};

export default function Sidebar({ samples, schema, llmAvailable, onAsk, onClear, hasHistory }) {
  const [schemaOpen, setSchemaOpen] = useState(false);

  return (
    <aside className="w-72 shrink-0 h-full overflow-y-auto border-r border-[var(--border)] bg-white/60 backdrop-blur px-4 py-5 flex flex-col gap-5">
      <div className="flex items-center gap-2 px-1">
        <div className="grid place-items-center w-9 h-9 rounded-xl bg-[var(--series-1)] text-white">
          <BarChart3 size={18} />
        </div>
        <div>
          <div className="text-sm font-bold leading-tight">Business Analyst</div>
          <div className="text-[11px] text-[var(--ink-muted)] leading-tight">Agentic AI · RAG</div>
        </div>
      </div>

      <div
        className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold"
        style={{
          background: llmAvailable ? "var(--status-good-bg)" : "#fdf1e0",
          color: llmAvailable ? "var(--status-good)" : "#b06b00",
        }}
      >
        <span
          className={`w-2 h-2 rounded-full ${llmAvailable ? "" : "pulse-dot"}`}
          style={{ background: llmAvailable ? "var(--status-good)" : "var(--status-warning)" }}
        />
        {llmAvailable ? "LLM-grounded answers" : "Rule-based mode (offline)"}
      </div>

      <div className="flex-1 flex flex-col gap-4">
        <div className="text-xs font-bold uppercase tracking-wide text-[var(--ink-muted)] px-1">
          Try asking
        </div>
        {Object.entries(samples).map(([group, questions]) => {
          const Icon = GROUP_ICONS[group] || Sparkles;
          return (
            <div key={group}>
              <div className="flex items-center gap-1.5 mb-1.5 px-1 text-xs font-semibold text-[var(--ink-secondary)]">
                <Icon size={13} /> {group}
              </div>
              <div className="flex flex-col gap-1">
                {questions.map((q) => (
                  <button
                    key={q}
                    onClick={() => onAsk(q)}
                    className="text-left text-[13px] leading-snug rounded-lg px-2.5 py-2 text-[var(--ink-primary)] hover:bg-[var(--series-1)]/8 hover:text-[var(--series-1)] transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div>
        <button
          onClick={() => setSchemaOpen((v) => !v)}
          className="w-full flex items-center justify-between rounded-lg px-2.5 py-2 text-xs font-semibold text-[var(--ink-secondary)] hover:bg-black/3"
        >
          <span className="flex items-center gap-1.5"><Database size={13} /> Database schema</span>
          <ChevronDown size={14} className={`transition-transform ${schemaOpen ? "rotate-180" : ""}`} />
        </button>
        {schemaOpen && (
          <pre className="mt-1 text-[10.5px] leading-relaxed bg-[var(--page)] rounded-lg p-2.5 overflow-x-auto text-[var(--ink-secondary)]">
{schema}
          </pre>
        )}
      </div>

      {hasHistory && (
        <button
          onClick={onClear}
          className="flex items-center justify-center gap-1.5 rounded-lg px-2.5 py-2 text-xs font-semibold text-[var(--ink-muted)] hover:text-[var(--status-critical)] hover:bg-[var(--status-critical-bg)] transition-colors"
        >
          <Trash2 size={13} /> Clear conversation
        </button>
      )}
    </aside>
  );
}
