import { AlertCircle, IndianRupee, PackageSearch, Send, ShoppingCart, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { askQuestion, getKpis, getSamples, getSchema, getStatus } from "../api";
import AnomalyBanner from "../components/AnomalyBanner";
import { AssistantBubble, UserBubble } from "../components/ChatMessage";
import KpiCard from "../components/KpiCard";
import Sidebar from "../components/Sidebar";

export default function AnalystPage() {
  const [kpis, setKpis] = useState(null);
  const [samples, setSamples] = useState({});
  const [schema, setSchema] = useState("");
  const [llmAvailable, setLlmAvailable] = useState(false);
  const [history, setHistory] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    getKpis().then(setKpis).catch(() => setError("Could not reach the API. Is the backend running on :8000?"));
    getSamples().then(setSamples).catch(() => {});
    getSchema().then((d) => setSchema(d.schema)).catch(() => {});
    getStatus().then((d) => setLlmAvailable(d.llm_available)).catch(() => {});
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [history, loading]);

  async function handleAsk(question) {
    if (!question.trim() || loading) return;
    setInput("");
    setError("");
    setLoading(true);
    setHistory((h) => [...h, { role: "user", text: question }]);
    try {
      const resp = await askQuestion(question);
      setHistory((h) => [...h, { role: "assistant", ...resp }]);
    } catch {
      setError("The agent hit an error answering that. Try rephrasing.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="h-full flex overflow-hidden">
      <Sidebar
        samples={samples}
        schema={schema}
        llmAvailable={llmAvailable}
        onAsk={handleAsk}
        onClear={() => setHistory([])}
        hasHistory={history.length > 0}
      />

      <main className="flex-1 flex flex-col min-w-0">
        <header className="px-6 pt-6 pb-4 border-b border-[var(--border)] bg-white/50 backdrop-blur">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-extrabold tracking-tight">Autonomous Business Data Analyst</h1>
            <span className="flex items-center gap-1 text-[11px] font-semibold text-[var(--series-1)] bg-[var(--series-1)]/10 px-2 py-0.5 rounded-full">
              <Sparkles size={11} /> RAG + Agentic AI
            </span>
          </div>
          <p className="text-sm text-[var(--ink-secondary)] mt-0.5">
            E-commerce analytics agent — ask a question, or click a sample in the sidebar.
          </p>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-5 flex flex-col gap-5" ref={scrollRef}>
          {kpis && (
            <div className="grid grid-cols-4 gap-3">
              <KpiCard icon={IndianRupee} label="Total Revenue" value={`₹${kpis.total_revenue.toLocaleString("en-IN")}`} sub="Jan – Aug 2026" accent="var(--series-1)" />
              <KpiCard icon={ShoppingCart} label="Total Orders" value={kpis.total_orders.toLocaleString("en-IN")} sub="Delivered / Shipped" accent="var(--series-3)" />
              <KpiCard icon={IndianRupee} label="Avg Order Value" value={`₹${kpis.avg_order_value.toLocaleString("en-IN")}`} sub="Per order" accent="var(--series-2)" />
              <KpiCard icon={AlertCircle} label="Active Alerts" value={kpis.active_anomalies} sub={`${kpis.low_stock_count} product(s) low on stock`} accent="var(--status-critical)" />
            </div>
          )}

          {kpis?.active_anomalies > 0 && (
            <AnomalyBanner months={kpis.anomaly_months} onExplain={() => handleAsk("Why did sales drop in July?")} />
          )}

          {error && (
            <div className="text-sm text-[var(--status-critical)] bg-[var(--status-critical-bg)] rounded-xl px-4 py-2.5">
              {error}
            </div>
          )}

          {history.length === 0 && !error && (
            <div className="flex-1 grid place-items-center text-center">
              <div className="max-w-sm">
                <div className="mx-auto mb-3 grid place-items-center w-12 h-12 rounded-2xl bg-[var(--series-1)]/10 text-[var(--series-1)]">
                  <PackageSearch size={22} />
                </div>
                <p className="text-sm text-[var(--ink-secondary)]">
                  No questions yet — try a sample from the sidebar, or type your own question below.
                </p>
              </div>
            </div>
          )}

          {history.map((item, i) =>
            item.role === "user" ? (
              <UserBubble key={i} text={item.text} />
            ) : (
              <AssistantBubble key={i} response={item} />
            )
          )}

          {loading && (
            <div className="animate-in flex items-center gap-2 text-sm text-[var(--ink-muted)] pl-11">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--series-1)] pulse-dot" />
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--series-1)] pulse-dot" style={{ animationDelay: "0.15s" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--series-1)] pulse-dot" style={{ animationDelay: "0.3s" }} />
              Agent is reasoning…
            </div>
          )}
        </div>

        <form
          onSubmit={(e) => { e.preventDefault(); handleAsk(input); }}
          className="px-6 py-4 border-t border-[var(--border)] bg-white/70 backdrop-blur"
        >
          <div className="flex items-center gap-2 rounded-2xl border border-[var(--border)] bg-white px-2 py-1.5 focus-within:border-[var(--series-1)] transition-colors">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a business question…"
              className="flex-1 bg-transparent px-2.5 py-2 text-[14px] outline-none placeholder:text-[var(--ink-muted)]"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="grid place-items-center w-9 h-9 rounded-xl bg-[var(--series-1)] text-white disabled:opacity-35 disabled:cursor-not-allowed hover:brightness-110 transition-all shrink-0"
            >
              <Send size={15} />
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
