"use client";

import { initials } from "@/lib/utils";

const TONES = [
  "linear-gradient(135deg,#e8b86d,#9a6428)",
  "linear-gradient(135deg,#8b9bff,#4f5fd6)",
  "linear-gradient(135deg,#3dcb9a,#1f8a5a)",
  "linear-gradient(135deg,#f07a6a,#c2413b)",
  "linear-gradient(135deg,#c9a36a,#6d4c2b)",
];

export function Monogram({ name, size = 40 }: { name: string; size?: number }) {
  const n = [...name].reduce((a, c) => a + c.charCodeAt(0), 0);
  return (
    <span
      className="inline-grid shrink-0 place-items-center rounded-xl text-[12px] font-semibold tracking-wide text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.35)]"
      style={{ width: size, height: size, background: TONES[n % TONES.length] }}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}
