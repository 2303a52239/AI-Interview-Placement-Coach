export function Loader({ label = "Loading..." }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-ink-faint">
      <div className="w-8 h-8 border-2 border-paper-line border-t-amber rounded-full animate-spin mb-3" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function EmptyState({ title, description, action }) {
  return (
    <div className="text-center py-16 px-6 border border-dashed border-paper-line rounded-card">
      <h3 className="font-display text-lg text-ink mb-1">{title}</h3>
      {description && <p className="text-sm text-ink-faint max-w-sm mx-auto mb-4">{description}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="text-center py-10 px-6 border border-clay/30 bg-clay/5 rounded-card">
      <p className="text-sm text-clay font-medium mb-3">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="text-sm underline text-clay">
          Try again
        </button>
      )}
    </div>
  );
}
