import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type Variant = "info" | "success" | "error";
type ToastItem = { id: string; message: string; variant: Variant };
type Ctx = { showToast: (message: string, variant?: Variant) => void };

const ToastContext = createContext<Ctx | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = useCallback((message: string, variant: Variant = "info") => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { id, message, variant }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 w-80" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`px-4 py-3 rounded-card border text-sm shadow-sm bg-paper-panel ${
              t.variant === "error"
                ? "border-clay text-clay"
                : t.variant === "success"
                ? "border-teal text-teal-dark"
                : "border-paper-line text-ink"
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
