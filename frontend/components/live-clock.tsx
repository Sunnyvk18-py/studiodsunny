"use client";

import { useEffect, useState } from "react";

export function LiveClock({ className = "" }: { className?: string }) {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    const tick = () => setNow(new Date());
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  if (!now) return <span className={className}>--:--</span>;

  const time = new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(now);

  return (
    <span className={className}>
      {time} <span className="text-muted">IST</span>
    </span>
  );
}
