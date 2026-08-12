"use client";

import { Badge, EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { formatINR, prettyStatus } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { useQuery } from "@tanstack/react-query";

export default function ReportsPage() {
  const { can } = useAuth();
  const q = useQuery({ queryKey: ["reports"], queryFn: endpoints.reports, enabled: can("reports:read") });

  if (!can("reports:read")) {
    return (
      <EmptyState title="Reports are restricted" body="Ask a founder or ops lead if you need access." />
    );
  }

  if (q.isError) {
    return <EmptyState title="Could not load reports" body={q.error.message} />;
  }

  if (q.isLoading || !q.data) {
    return (
      <div className="mx-auto max-w-5xl space-y-3">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  const d = q.data;
  const showFinance = can("finance:read");

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        kicker="Insights"
        title="Reports"
        description="Revenue, utilization, conversion, and project health — live from HQ data."
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {showFinance ? (
          <>
            <Stat label="Collected" value={formatINR(d.revenue_collected)} />
            <Stat label="Outstanding" value={formatINR(d.revenue_outstanding)} tone="warn" />
            <Stat label="Overdue" value={formatINR(d.revenue_overdue)} tone="danger" />
            <Stat label="Invoices paid" value={`${d.paid_count}/${d.invoice_count}`} />
          </>
        ) : null}
        <Stat label="Lead conversion" value={`${d.lead_conversion_pct}%`} />
        <Stat label="Utilization" value={`${d.utilization_pct}%`} tone={d.utilization_pct >= 85 ? "warn" : undefined} />
        <Stat label="Active projects" value={String(d.active_projects)} />
        <Stat label="At risk" value={String(d.at_risk_projects)} tone={d.at_risk_projects ? "danger" : undefined} />
        <Stat label="Clients" value={String(d.active_clients)} />
        <Stat label="Headcount" value={String(d.headcount)} />
        <Stat label="Open tasks" value={String(d.open_tasks)} />
        <Stat label="Leads won" value={`${d.lead_won}/${d.lead_total}`} />
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <SeriesCard title="Leads by stage" rows={d.leads_by_stage} />
        <SeriesCard title="Projects by health" rows={d.projects_by_health} />
        {showFinance ? <SeriesCard title="Invoices by status" rows={d.invoices_by_status} /> : null}
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "warn" | "danger" }) {
  return (
    <div className="panel p-4">
      <p className="text-[12px] text-muted">{label}</p>
      <p
        className={`mt-1 text-[22px] font-semibold tabular-nums tracking-tight ${
          tone === "danger" ? "text-danger" : tone === "warn" ? "text-warn" : "text-ink"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function SeriesCard({ title, rows }: { title: string; rows: { label: string; value: number }[] }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <div className="panel p-4">
      <h2 className="section-title mb-3">{title}</h2>
      {rows.length === 0 ? (
        <p className="text-[13px] text-muted">No data.</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((r) => (
            <li key={r.label}>
              <div className="mb-1 flex items-center justify-between text-[12px]">
                <span className="text-muted">{prettyStatus(r.label)}</span>
                <Badge>{r.value}</Badge>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-sunken">
                <div className="h-full rounded-full bg-accent" style={{ width: `${(r.value / max) * 100}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
