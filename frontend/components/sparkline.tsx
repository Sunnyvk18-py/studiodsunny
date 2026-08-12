"use client";

const SERIES: Record<string, number[]> = {
  clients: [4, 4, 5, 5, 6, 6, 6],
  projects: [5, 6, 7, 7, 8, 8, 8],
  team: [4, 4, 5, 5, 5, 5, 5],
  leads: [3, 5, 4, 7, 6, 8, 9],
  revenue: [1.8, 2.1, 2.0, 2.4, 2.6, 2.5, 2.85],
  outstanding: [0.72, 0.68, 0.61, 0.55, 0.52, 0.5, 0.48],
  risk: [2, 2, 1, 2, 1, 1, 1],
  util: [71, 74, 78, 80, 82, 86, 84],
};

export function Sparkline({
  seriesKey,
  tone = "accent",
}: {
  seriesKey: string;
  tone?: "accent" | "ok" | "warn" | "danger" | "info";
}) {
  const values = SERIES[seriesKey] || SERIES.projects;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const w = 72;
  const h = 28;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - 3 - ((v - min) / span) * (h - 8);
    return `${x},${y}`;
  });
  const color = {
    accent: "var(--accent)",
    ok: "var(--ok)",
    warn: "var(--warn)",
    danger: "var(--danger)",
    info: "var(--accent-2)",
  }[tone];

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="overflow-visible" aria-hidden>
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={pts.join(" ")}
        opacity="0.95"
      />
      <circle cx={pts.at(-1)?.split(",")[0]} cy={pts.at(-1)?.split(",")[1]} r="2.2" fill={color} />
    </svg>
  );
}
