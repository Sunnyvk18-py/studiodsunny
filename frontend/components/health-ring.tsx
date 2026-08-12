"use client";

export function HealthRing({
  value,
  label,
  tone = "accent",
}: {
  value: number;
  label: string;
  tone?: "accent" | "ok" | "warn" | "danger" | "info";
}) {
  const r = 18;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, value));
  const color = {
    accent: "var(--accent)",
    ok: "var(--ok)",
    warn: "var(--warn)",
    danger: "var(--danger)",
    info: "var(--accent-2)",
  }[tone];

  return (
    <div className="flex items-center gap-3">
      <svg width="48" height="48" viewBox="0 0 48 48" aria-hidden>
        <circle cx="24" cy="24" r={r} fill="none" stroke="var(--line)" strokeWidth="4" />
        <circle
          cx="24"
          cy="24"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c - (pct / 100) * c}
          transform="rotate(-90 24 24)"
        />
      </svg>
      <div>
        <p className="text-[16px] font-semibold tabular-nums tracking-tight">{pct}%</p>
        <p className="text-[12px] text-muted">{label}</p>
      </div>
    </div>
  );
}
