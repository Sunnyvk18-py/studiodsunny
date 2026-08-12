"use client";

import { Avatar, Button, Skeleton } from "@/components/ui";
import { Sparkline } from "@/components/sparkline";
import { HealthRing } from "@/components/health-ring";
import { useAuth } from "@/lib/auth";
import { endpoints } from "@/lib/api";
import { greetingFor } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { format, formatDistanceToNow } from "date-fns";
import {
  ArrowUpRight,
  Bot,
  Briefcase,
  Building2,
  CircleDollarSign,
  FolderKanban,
  Plus,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useUI } from "@/stores/ui";

const KPI_META: Record<string, { icon: typeof FolderKanban; tone: "accent" | "ok" | "warn" | "danger" | "info" }> = {
  clients: { icon: Building2, tone: "info" },
  projects: { icon: FolderKanban, tone: "accent" },
  team: { icon: Users, tone: "ok" },
  leads: { icon: Briefcase, tone: "info" },
  revenue: { icon: CircleDollarSign, tone: "ok" },
  outstanding: { icon: CircleDollarSign, tone: "warn" },
  risk: { icon: FolderKanban, tone: "danger" },
  util: { icon: Users, tone: "warn" },
};

export default function HomePage() {
  const { user, can } = useAuth();
  const setQuick = useUI((s) => s.setQuickCreateOpen);
  const q = useQuery({ queryKey: ["dashboard"], queryFn: endpoints.dashboard });

  if (q.isLoading || !q.data) {
    return (
      <div className="grid gap-3 md:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
    );
  }

  const data = q.data;
  const today = new Date();
  const util = Number(data.health.utilization ?? 84);
  const kpis = data.kpis.filter((kpi) => {
    if (kpi.key === "revenue" || kpi.key === "outstanding") return can("finance:read");
    if (kpi.key === "leads") return can("leads:read");
    if (kpi.key === "clients") return can("clients:read");
    if (kpi.key === "team") return can("employees:read");
    return true;
  });
  const quickActions = (
    [
      ["/projects/new", "New Project", null],
      ["/clients/new", "Add Client", "clients:write"],
      ["/team?new=1", "Add Employee", "employees:write"],
      ["/tasks?new=1", "Create Task", null],
      ["/leads", "Add Lead", "leads:write"],
      ["/finance", "Create Invoice", "finance:write"],
      ["/calendar", "Schedule Meeting", null],
      ["/desk", "My Desk", null],
    ] as const
  ).filter(([, , perm]) => !perm || can(perm));

  return (
    <div className="mx-auto max-w-[1200px]">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="kicker mb-2">{format(today, "EEEE · MMMM d")}</p>
          <h1 className="text-[26px] font-semibold leading-[1.2] tracking-[-0.02em] text-ink md:text-[32px]">
            {greetingFor()}, {data.greeting_name}.
          </h1>
          <p className="mt-2 text-[14px] text-muted">Studio Sunny is in motion. Here’s the floor.</p>
        </div>
        <Button onClick={() => setQuick(true)}>
          <Plus className="size-4" /> New
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi) => {
          const meta = KPI_META[kpi.key] || KPI_META.projects;
          const Icon = meta.icon;
          return (
            <div key={kpi.key} className="panel lift px-4 py-3.5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[12px] font-medium text-muted">{kpi.label}</p>
                  <p className="mt-1.5 text-[24px] font-semibold tabular-nums tracking-tight text-ink">{kpi.value}</p>
                </div>
                <span className="grid size-8 place-items-center rounded-lg bg-sunken text-accent">
                  <Icon className="size-4" strokeWidth={1.75} />
                </span>
              </div>
              <div className="mt-3 flex items-end justify-between gap-2">
                {kpi.delta != null ? (
                  <p className={`text-[12px] font-medium ${kpi.delta >= 0 ? "text-ok" : "text-danger"}`}>
                    {kpi.delta >= 0 ? "↑" : "↓"} {Math.abs(kpi.delta)}% {kpi.delta_label}
                  </p>
                ) : (
                  <p className="text-[12px] text-muted">{kpi.delta_label}</p>
                )}
                <Sparkline seriesKey={kpi.key} tone={meta.tone} />
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1.25fr)_minmax(300px,0.75fr)]">
        <section className="panel p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="grid size-8 place-items-center rounded-lg bg-accent/15 text-accent">
                <Bot className="size-4" />
              </span>
              <h2 className="section-title">Sunny AI briefing</h2>
            </div>
            <Link href="/ai" className="text-[12px] font-semibold text-accent hover:underline">
              Ask anything
            </Link>
          </div>
          <div className="whitespace-pre-line text-[14px] leading-6 text-ink/90">{data.briefing}</div>
          <div className="mt-5 border-t border-line pt-4">
            <p className="kicker mb-3">Recommended</p>
            <ol className="space-y-2 text-[13px]">
              {data.recommended_actions.map((a, i) => (
                <li key={a} className="flex gap-3 rounded-lg bg-sunken/60 px-3 py-2">
                  <span className="font-semibold text-accent">{String(i + 1).padStart(2, "0")}</span>
                  <span>{a}</span>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <div className="space-y-3">
          <section className="panel p-5">
            <h2 className="section-title mb-4">Needs attention</h2>
            {data.attention.length === 0 ? (
              <p className="text-[13px] text-muted">All clear.</p>
            ) : (
              <ul className="space-y-1.5">
                {data.attention.map((item) => (
                  <li key={item.title}>
                    <Link
                      href={item.href || "/home"}
                      className="flex items-center gap-2.5 rounded-xl border border-line bg-sunken/40 px-3 py-2.5 hover:border-accent/30"
                    >
                      <span
                        className={`size-2 shrink-0 rounded-full ${item.severity === "critical" ? "bg-danger" : "bg-warn"}`}
                      />
                      <span className="min-w-0 flex-1 text-[13px]">{item.title}</span>
                      <ArrowUpRight className="size-3.5 text-muted" />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="panel p-5">
            <h2 className="section-title mb-4">Company health</h2>
            <div className="grid grid-cols-2 gap-4">
              <HealthRing value={util} label="Utilization" tone={util >= 90 ? "danger" : util >= 80 ? "warn" : "ok"} />
              <HealthRing
                value={Math.min(100, Number(data.health.projects ?? 8) * 10)}
                label="Delivery load"
                tone="accent"
              />
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-line pt-4 text-[13px]">
              <div>
                <dt className="text-[12px] text-muted">Open tasks</dt>
                <dd className="mt-0.5 font-semibold tabular-nums">{String(data.health.open_tasks ?? "—")}</dd>
              </div>
              <div>
                <dt className="text-[12px] text-muted">Active clients</dt>
                <dd className="mt-0.5 font-semibold tabular-nums">{String(data.health.active_clients ?? "—")}</dd>
              </div>
            </dl>
            {user?.role_key !== "founder" && user?.role_key !== "finance" ? (
              <p className="mt-3 text-[12px] text-muted">Financial metrics hidden for your role.</p>
            ) : null}
          </section>
        </div>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)]">
        <section className="panel p-5">
          <h2 className="section-title mb-4">Activity</h2>
          <ul className="space-y-3">
            {data.activity.map((a) => (
              <li key={a.id} className="flex items-start gap-3">
                <Avatar name={a.actor?.display_name || "HQ"} size={28} />
                <div className="min-w-0">
                  <p className="text-[13px] text-ink">{a.summary}</p>
                  <p className="text-[12px] text-muted">
                    {formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel p-5">
          <h2 className="section-title mb-4">Quick actions</h2>
          <div className="grid grid-cols-2 gap-2">
            {quickActions.map(([href, label]) => (
              <Link
                key={href}
                href={href}
                className="rounded-xl border border-line bg-sunken/40 px-3 py-2.5 text-[13px] font-medium hover:border-accent/35 hover:bg-sunken"
              >
                {label}
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
