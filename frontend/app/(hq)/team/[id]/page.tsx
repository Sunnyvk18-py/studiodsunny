"use client";

import { Badge, PageHeader, Skeleton } from "@/components/ui";
import { ROLE_LABELS, endpoints } from "@/lib/api";
import { formatINR, prettyStatus } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

export default function EmployeeProfilePage() {
  const { id } = useParams<{ id: string }>();
  const { user, can } = useAuth();
  const emp = useQuery({ queryKey: ["employee", id], queryFn: () => endpoints.employee(id) });
  const tasks = useQuery({ queryKey: ["tasks", "emp", id], queryFn: () => endpoints.tasks(), enabled: !!emp.data });

  if (emp.isLoading || !emp.data) return <Skeleton className="h-64" />;
  const e = emp.data;
  const mine = (tasks.data || []).filter((t) => t.assignee_id === e.user_id);
  const showComp = can("employees.compensation:read") || user?.id === e.user_id;

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        kicker={e.department_name || ROLE_LABELS[e.role_key]}
        title={e.display_name}
        description={`${e.job_title} · ${e.location || "—"}`}
        actions={<Badge tone={e.availability === "busy" ? "warn" : "ok"}>{prettyStatus(e.availability)}</Badge>}
      />

      <div className="grid gap-3 md:grid-cols-4">
        <Stat label="Active projects" value={String(e.active_projects)} />
        <Stat label="Utilization" value={`${e.utilization}%`} gold />
        <Stat label="Leave balance" value={showComp ? `${e.leave_balance_days} days` : "—"} />
        <Stat label="Employment" value={prettyStatus(e.employment_type)} />
      </div>

      <section className="panel mt-6 p-5">
        <h2 className="section-title mb-3">Overview</h2>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <Row k="Email" v={e.email} />
          <Row k="Role" v={ROLE_LABELS[e.role_key]} />
          <Row k="Joined" v={e.joining_date || "—"} />
          {showComp ? <Row k="Compensation" v={e.salary ? `${e.salary_currency} ${formatINR(Number(e.salary)).replace("₹", "")}/mo` : "—"} /> : null}
          <Row k="Skills" v={e.skills?.join(", ") || "—"} />
        </dl>
        {!showComp ? <p className="mt-4 text-xs text-muted">Compensation is restricted.</p> : null}
      </section>

      <section className="mt-6">
        <h2 className="section-title mb-3">Tasks</h2>
        <div className="space-y-2">
          {mine.slice(0, 12).map((t) => (
            <div key={t.id} className="panel lift flex items-center justify-between p-3 text-sm">
              <span>{t.title}</span>
              <span className="text-xs text-muted">{prettyStatus(t.status)}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Stat({ label, value, gold }: { label: string; value: string; gold?: boolean }) {
  return (
    <div className="panel p-4">
      <p className="text-[12px] text-muted">{label}</p>
      <p className={`mt-1 text-[20px] font-semibold tabular-nums tracking-tight ${gold ? "gold-num" : ""}`}>{value}</p>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <dt className="text-muted">{k}</dt>
      <dd className="mt-0.5 text-ink">{v}</dd>
    </div>
  );
}
