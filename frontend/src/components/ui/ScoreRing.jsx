export function ScoreRing({ value = 0, size = 96, strokeWidth = 8, label, sublabel }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, value));
  const offset = circumference - (clamped / 100) * circumference;

  const color = clamped >= 75 ? "rgb(var(--teal))" : clamped >= 50 ? "rgb(var(--amber))" : "rgb(var(--clay))";

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="rgb(var(--line))" strokeWidth={strokeWidth} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
        <text
          x="50%"
          y="50%"
          dominantBaseline="middle"
          textAnchor="middle"
          className="font-mono"
          fontSize={size * 0.24}
          fill="rgb(var(--ink))"
          fontWeight="600"
        >
          {Math.round(clamped)}
        </text>
      </svg>
      {label && <p className="text-sm font-medium text-ink mt-2">{label}</p>}
      {sublabel && <p className="text-xs text-ink-faint">{sublabel}</p>}
    </div>
  );
}
