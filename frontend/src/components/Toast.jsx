import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";
import { createContext, useCallback, useContext, useRef, useState } from "react";

const ToastContext = createContext(null);
export const useToast = () => useContext(ToastContext);

const STYLES = {
  success: { icon: CheckCircle2, bg: "var(--status-good-bg)", fg: "#0a7a0a" },
  error: { icon: AlertTriangle, bg: "var(--status-critical-bg)", fg: "var(--status-critical)" },
  info: { icon: Info, bg: "#eaf2fc", fg: "var(--series-1)" },
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const show = useCallback((text, type = "info", duration = 4000) => {
    const id = nextId.current++;
    setToasts((t) => [...t, { id, text, type }]);
    if (duration) setTimeout(() => dismiss(id), duration);
    return id;
  }, [dismiss]);

  const toast = {
    show,
    success: (text, duration) => show(text, "success", duration),
    error: (text, duration) => show(text, "error", duration),
    info: (text, duration) => show(text, "info", duration),
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="fixed bottom-5 right-5 z-[100] flex flex-col gap-2 w-full max-w-sm pointer-events-none">
        {toasts.map((t) => {
          const { icon: Icon, bg, fg } = STYLES[t.type];
          return (
            <div
              key={t.id}
              className="animate-in pointer-events-auto flex items-start gap-2.5 rounded-xl shadow-lg px-3.5 py-3 text-[13px] font-medium"
              style={{ background: bg, color: fg }}
            >
              <Icon size={16} className="shrink-0 mt-0.5" />
              <span className="flex-1 leading-snug">{t.text}</span>
              <button onClick={() => dismiss(t.id)} className="shrink-0 opacity-60 hover:opacity-100 transition-opacity">
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
