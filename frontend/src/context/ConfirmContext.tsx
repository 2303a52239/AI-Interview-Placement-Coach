import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

type Options = { title?: string; message?: string; confirmLabel?: string; cancelLabel?: string; danger?: boolean };
type Confirm = (options: Options) => Promise<boolean>;

const ConfirmContext = createContext<Confirm | null>(null);

/**
 * Promise-based confirmation dialog:
 *   const confirm = useConfirm();
 *   if (await confirm({ title, message, confirmLabel, danger })) { ... }
 */
export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [dialog, setDialog] = useState<Options | null>(null);
  const resolverRef = useRef<((v: boolean) => void) | null>(null);

  const confirm = useCallback((options: Options) => {
    return new Promise<boolean>((resolve) => {
      resolverRef.current = resolve;
      setDialog(options);
    });
  }, []);

  const close = (result: boolean) => {
    resolverRef.current?.(result);
    resolverRef.current = null;
    setDialog(null);
  };

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {dialog && (
        <div
          className="fixed inset-0 z-50 bg-ink/50 flex items-center justify-center px-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-title"
          onKeyDown={(e) => e.key === "Escape" && close(false)}
        >
          <div className="bg-paper-panel rounded-card border border-paper-line max-w-sm w-full p-6 tick-corner">
            <h2 id="confirm-title" className="font-display text-lg mb-2">{dialog.title || "Are you sure?"}</h2>
            <p className="text-sm text-ink-soft mb-6">{dialog.message}</p>
            <div className="flex justify-end gap-3">
              <button
                autoFocus
                onClick={() => close(false)}
                className="px-4 py-2 text-sm rounded-card border border-paper-line hover:bg-paper focus-ring"
              >
                {dialog.cancelLabel || "Cancel"}
              </button>
              <button
                onClick={() => close(true)}
                className={`px-4 py-2 text-sm rounded-card font-medium focus-ring ${
                  dialog.danger ? "bg-clay text-white" : "bg-amber text-ink hover:bg-amber-dark"
                }`}
              >
                {dialog.confirmLabel || "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error("useConfirm must be used within ConfirmProvider");
  return ctx;
}
