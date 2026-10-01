import { BarChart3, Heart } from "lucide-react";

const YEAR = new Date().getFullYear();

// `compact`: a thin single-line bar for inside the authenticated app shell.
// Default: a fuller footer for the public auth pages (login/register/status).
export default function Footer({ compact = false }) {
  if (compact) {
    return (
      <footer className="shrink-0 h-9 flex items-center justify-between px-5 border-t border-[var(--border)] bg-white/70 text-[11.5px] text-[var(--ink-muted)]">
        <span>© {YEAR} Nexus AI · Autonomous Business Data Analyst</span>
        <span className="hidden sm:flex items-center gap-1.5">
          Built with <Heart size={11} className="text-[var(--status-critical)] fill-current" /> for PPD II
        </span>
      </footer>
    );
  }

  return (
    <footer className="shrink-0 border-t border-[var(--border)] bg-white/60 px-6 py-5">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-[12.5px] text-[var(--ink-muted)]">
        <div className="flex items-center gap-2">
          <span className="grid place-items-center w-6 h-6 rounded-md bg-[var(--series-1)] text-white"><BarChart3 size={13} /></span>
          <span>© {YEAR} Nexus AI. All rights reserved.</span>
        </div>
        <span>RAG + Agentic AI · PPD II Major Project</span>
      </div>
    </footer>
  );
}
