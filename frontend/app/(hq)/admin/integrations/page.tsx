"use client";

import { Badge, PageHeader, Skeleton } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";

export default function IntegrationsPage() {
  const q = useQuery({ queryKey: ["integrations"], queryFn: endpoints.integrations, refetchInterval: 30_000 });

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        kicker="Platform"
        title="Integrations"
        description="Live status of SSO, observability, Redis, Arq workers, and email. Wire keys in .env — no redeploy of this page needed."
      />
      {q.isLoading ? (
        <Skeleton className="h-64" />
      ) : (
        <div className="panel divide-y divide-line">
          {(q.data || []).map((row) => (
            <div key={row.key} className="flex flex-wrap items-start justify-between gap-3 px-4 py-3.5">
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-[14px] font-medium text-ink">{row.label}</p>
                  <Badge tone={row.configured ? "ok" : "warn"}>{row.configured ? "Ready" : "Not set"}</Badge>
                </div>
                <p className="mt-1 text-[13px] text-muted">{row.detail}</p>
                {row.docs_hint ? <p className="mt-1 font-mono text-[11px] text-muted">{row.docs_hint}</p> : null}
              </div>
            </div>
          ))}
        </div>
      )}
      <p className="mt-4 text-[12px] text-muted">
        Worker: <code className="font-mono">npm run worker</code> · Compose:{" "}
        <code className="font-mono">docker compose --profile workers up</code>
      </p>
    </div>
  );
}
