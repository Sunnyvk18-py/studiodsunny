"use client";

import { cn, initials } from "@/lib/utils";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { ButtonHTMLAttributes, InputHTMLAttributes, TextareaHTMLAttributes } from "react";

const AVATAR_TONES = [
  "linear-gradient(135deg,oklch(0.80 0.11 75),oklch(0.52 0.09 60))",
  "linear-gradient(135deg,oklch(0.72 0.13 275),oklch(0.52 0.16 275))",
  "linear-gradient(135deg,oklch(0.75 0.14 165),oklch(0.52 0.12 165))",
  "linear-gradient(135deg,oklch(0.68 0.19 25),oklch(0.55 0.18 25))",
];

function toneFor(name: string) {
  const n = [...name].reduce((a, c) => a + c.charCodeAt(0), 0);
  return AVATAR_TONES[n % AVATAR_TONES.length];
}

export function Avatar({ name, size = 28 }: { name: string; size?: number }) {
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full text-[11px] font-medium tracking-wide text-white"
      style={{ width: size, height: size, background: toneFor(name) }}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}

export function Button({
  variant = "primary",
  className,
  loading,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "outline" | "danger" | "subtle";
  loading?: boolean;
}) {
  const styles = {
    primary: "bg-accent text-accent-fg hover:brightness-105",
    ghost: "hover:bg-sunken text-ink",
    outline: "border border-line hover:bg-sunken hover:border-[var(--hairline-strong)]",
    danger: "bg-danger/12 text-danger hover:bg-danger/18",
    subtle: "bg-sunken text-ink hover:bg-elevated",
  }[variant];
  return (
    <button
      className={cn(
        "inline-flex h-9 items-center justify-center gap-1.5 rounded-md px-3 text-[14px] font-medium transition disabled:opacity-50",
        styles,
        className,
      )}
      {...props}
    >
      {loading ? <Loader2 className="size-3.5 animate-spin" /> : null}
      {props.children}
    </button>
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-10 w-full rounded-md border border-line bg-bg px-3 text-[14px] text-ink placeholder:text-muted outline-none transition focus:border-accent",
        className,
      )}
      {...props}
    />
  );
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "min-h-24 w-full rounded-md border border-line bg-bg px-3 py-2 text-[14px] text-ink placeholder:text-muted outline-none focus:border-accent",
        className,
      )}
      {...props}
    />
  );
}

export function Select({
  className,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-10 w-full rounded-md border border-line bg-bg px-3 text-[14px] text-ink outline-none focus:border-accent",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: React.ReactNode;
  tone?: "neutral" | "ok" | "warn" | "danger" | "accent" | "info";
  className?: string;
}) {
  const tones = {
    neutral: "bg-sunken text-muted",
    ok: "bg-ok/14 text-ok",
    warn: "bg-warn/14 text-warn",
    danger: "bg-danger/14 text-danger",
    accent: "bg-accent/14 text-accent",
    info: "bg-[color-mix(in_oklch,var(--accent-2)_16%,transparent)] text-[var(--accent-2)]",
  }[tone];
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded-full px-2 text-[12px] font-medium capitalize",
        tones,
        className,
      )}
    >
      {children}
    </span>
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="panel flex flex-col items-start gap-2 p-7">
      <p className="font-display text-[28px] text-ink">{title}</p>
      <p className="max-w-md text-[14px] text-muted">{body}</p>
      {action}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-sunken", className)} />;
}

export function PageHeader({
  kicker,
  title,
  description,
  actions,
}: {
  kicker?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        {kicker ? <p className="kicker mb-2">{kicker}</p> : null}
        <h1 className="text-[26px] font-semibold leading-[1.2] tracking-[-0.018em] text-ink md:text-[32px]">{title}</h1>
        {description ? <p className="mt-1.5 max-w-2xl text-[14px] text-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function ComingSoon({ title, body }: { title: string; body: string }) {
  return (
    <div className="mx-auto max-w-xl py-16">
      <div className="panel p-8 text-center">
        <p className="kicker mb-3">Coming next</p>
        <h1 className="font-display text-[32px] text-ink">{title}</h1>
        <p className="mx-auto mt-3 max-w-md text-[14px] leading-6 text-muted">{body}</p>
        <Link href="/home" className="mt-6 inline-flex text-[14px] font-medium text-accent hover:underline">
          Back to Home
        </Link>
      </div>
    </div>
  );
}

export function healthTone(health: string): "ok" | "warn" | "danger" | "neutral" {
  if (health === "healthy") return "ok";
  if (health === "needs_attention") return "warn";
  if (health === "at_risk" || health === "critical") return "danger";
  return "neutral";
}

export function priorityTone(priority: string): "ok" | "warn" | "danger" | "accent" | "neutral" {
  if (priority === "urgent") return "danger";
  if (priority === "high") return "warn";
  if (priority === "medium") return "accent";
  return "neutral";
}
