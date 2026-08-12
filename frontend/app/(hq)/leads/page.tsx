"use client";

import { Badge, EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { formatINR, prettyStatus } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";

const STAGES = ["new_lead", "contacted", "discovery_call", "qualified", "proposal_sent", "negotiation", "won", "lost"];

export default function LeadsPage() {
  const q = useQuery({ queryKey: ["leads"], queryFn: endpoints.leads });

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader kicker="Pipeline" title="Leads" description="From first hello to a signed engagement." />
      {q.isError ? (
        <EmptyState title="Restricted" body="Lead pipeline is limited to sales, operations, and leadership." />
      ) : q.isLoading ? (
        <Skeleton className="h-64" />
      ) : (
        <div className="grid gap-3 md:grid-cols-4 xl:grid-cols-8">
          {STAGES.map((stage) => {
            const items = (q.data || []).filter((l) => l.stage === stage);
            return (
              <div key={stage} className="rounded-2xl border border-line bg-sunken/40 p-3">
                <div className="mb-3 flex items-center justify-between">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
                    {prettyStatus(stage)}
                  </p>
                  <span className="gold-num text-[12px] font-semibold">{items.length}</span>
                </div>
                <div className="space-y-2">
                  {items.map((l) => (
                    <div key={l.id} className="panel lift p-3">
                      <p className="text-[13px] font-semibold">{l.business_name}</p>
                      <p className="mt-1 text-[11px] text-muted">{l.requested_service || l.industry}</p>
                      <p className="mt-2 text-[13px] font-semibold tabular-nums text-accent">
                        {formatINR(Number(l.estimated_value))}
                      </p>
                      <Badge tone="info" className="mt-2">
                        {l.probability}%
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
