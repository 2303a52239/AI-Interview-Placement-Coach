export function Card({ children, className = "", tick = false, ...props }) {
  return (
    <div
      className={`bg-paper-panel border border-paper-line rounded-card ${tick ? "tick-corner" : ""} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function Button({ children, variant = "primary", className = "", as = "button", ...props }) {
  const base =
    "inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium rounded-card transition-colors focus-ring disabled:opacity-50 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-ink text-paper hover:bg-ink-soft",
    accent: "bg-amber text-ink hover:bg-amber-dark",
    outline: "border border-ink text-ink hover:bg-ink hover:text-paper",
    ghost: "text-ink hover:bg-paper-line/60",
    danger: "bg-clay text-white hover:opacity-90",
  };
  const Comp = as;
  return (
    <Comp className={`${base} ${variants[variant] || variants.primary} ${className}`} {...props}>
      {children}
    </Comp>
  );
}

export function Badge({ children, tone = "neutral" }) {
  const tones = {
    neutral: "bg-paper-line text-ink-soft",
    amber: "bg-amber-light text-amber-dark",
    teal: "bg-teal-light text-teal-dark",
    clay: "bg-clay/10 text-clay",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function SectionHeading({ eyebrow, title, description }) {
  return (
    <div className="mb-6">
      {eyebrow && <p className="text-sm text-teal font-medium mb-1">{eyebrow}</p>}
      <h1 className="text-2xl font-display font-medium text-ink">{title}</h1>
      {description && <p className="text-ink-faint mt-1 text-sm max-w-xl">{description}</p>}
    </div>
  );
}
