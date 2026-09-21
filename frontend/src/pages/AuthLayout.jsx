import { BarChart3, Building2, ShieldCheck, Sparkles } from "lucide-react";

const POINTS = [
  { icon: Sparkles, title: "Ask in plain English", text: "Get answers, charts and root-cause analysis from your own e-commerce data." },
  { icon: Building2, title: "Built for your whole team", text: "Finance controls the data; every leader sees the insights they need." },
  { icon: ShieldCheck, title: "Verified companies only", text: "Every organisation is reviewed before it gets access to the platform." },
];

export default function AuthLayout({ children, wide = false }) {
  return (
    <div className="min-h-screen flex">
      <aside className="hidden lg:flex w-[42%] flex-col justify-between p-10 text-white"
        style={{ background: "linear-gradient(155deg, #2a78d6 0%, #184f95 55%, #0d366b 100%)" }}>
        <div className="flex items-center gap-2.5">
          <span className="grid place-items-center w-10 h-10 rounded-xl bg-white/15"><BarChart3 size={20} /></span>
          <span className="text-xl font-extrabold tracking-tight">Nexus AI</span>
        </div>
        <div>
          <h1 className="text-4xl font-extrabold leading-tight tracking-tight">
            The autonomous business analyst for e-commerce.
          </h1>
          <div className="mt-8 space-y-5">
            {POINTS.map(({ icon: Icon, title, text }) => (
              <div key={title} className="flex gap-3.5">
                <span className="grid place-items-center w-9 h-9 rounded-lg bg-white/12 shrink-0"><Icon size={17} /></span>
                <div>
                  <div className="font-semibold">{title}</div>
                  <div className="text-sm text-white/75 leading-snug">{text}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="text-xs text-white/55">RAG + Agentic AI · PPD II project</div>
      </aside>
      <main className="flex-1 grid place-items-center px-5 py-10 overflow-y-auto">
        <div className={`w-full ${wide ? "max-w-2xl" : "max-w-sm"}`}>{children}</div>
      </main>
    </div>
  );
}
