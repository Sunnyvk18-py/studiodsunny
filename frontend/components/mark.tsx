export function Mark({ className = "size-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <defs>
        <linearGradient id="ss-mark" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--accent)" />
          <stop offset="100%" stopColor="var(--accent-2)" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill="url(#ss-mark)" />
      <rect x="1.2" y="1.2" width="29.6" height="29.6" rx="8" fill="none" stroke="rgba(255,255,255,0.28)" strokeWidth="1" />
      <path
        d="M10 12.2c0-2.1 1.7-3.5 4.4-3.5 2.4 0 4 1.1 4.2 2.8h-2.15c-.2-.7-.9-1.15-2.05-1.15-1.2 0-2 .55-2 1.35 0 .7.55 1.1 2.35 1.45l1.15.22c2.35.45 3.55 1.45 3.55 3.2 0 2.2-1.85 3.65-4.7 3.65-2.7 0-4.5-1.25-4.75-3.15h2.2c.25.85 1.15 1.4 2.5 1.4 1.4 0 2.25-.55 2.25-1.45 0-.7-.55-1.15-2.4-1.5l-1.2-.25C11.15 15.5 10 14.4 10 12.2z"
        fill="var(--accent-fg)"
      />
    </svg>
  );
}
