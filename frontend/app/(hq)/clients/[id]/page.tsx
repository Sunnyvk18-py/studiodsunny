"use client";

import { Badge, Button, PageHeader, Skeleton } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { formatINR, prettyStatus } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const client = useQuery({ queryKey: ["client", id], queryFn: () => endpoints.client(id) });
  const projects = useQuery({ queryKey: ["projects", "client", id], queryFn: () => endpoints.projects({ client_id: id }) });

  if (client.isLoading || !client.data) return <Skeleton className="h-64" />;
  const c = client.data;
  const stepPct = Math.round(((c.onboarding_complete ? 8 : c.onboarding_step) / 8) * 100);

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        kicker={c.industry || "Client"}
        title={c.business_name}
        description={c.notes || `${c.primary_contact_name || ""} · ${c.location || ""}`}
        actions={
          <Link href={`/projects/new?client=${c.id}`}>
            <Button>New project</Button>
          </Link>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Info label="Contact" value={c.primary_contact_name || "—"} />
        <Info label="Email" value={c.email || "—"} />
        <Info label="Phone" value={c.phone || "—"} />
        <Info label="Status" value={prettyStatus(c.status)} />
      </div>

      <section className="panel mt-6 p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="section-title">Onboarding</h2>
          <span className="gold-num text-[13px] font-semibold">{stepPct}%</span>
        </div>
        <div className="progress-track h-1.5">
          <div className="progress-fill" style={{ width: `${stepPct}%` }} />
        </div>
        <ol className="mt-4 grid gap-2 text-sm md:grid-cols-4">
          {["Company details", "Requirements", "Brand assets", "Content", "Technical", "Domain / hosting", "Approvals", "Kickoff"].map(
            (s, i) => (
              <li key={s} className={i < c.onboarding_step || c.onboarding_complete ? "text-ink" : "text-muted"}>
                {i + 1}. {s}
              </li>
            ),
          )}
        </ol>
      </section>

      <section className="mt-6">
        <h2 className="section-title mb-2">Projects</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {(projects.data || []).map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`} className="panel lift p-4">
              <div className="flex justify-between">
                <p className="font-medium">{p.name}</p>
                <Badge>{prettyStatus(p.status)}</Badge>
              </div>
              <p className="mt-2 text-xs text-muted">{p.progress}% · {p.project_type}</p>
            </Link>
          ))}
        </div>
      </section>

      {c.pending_invoices ? (
        <p className="mt-6 text-sm text-warn">Pending invoices: {formatINR(Number(c.pending_invoices))}</p>
      ) : null}
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="panel p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-sm">{value}</p>
    </div>
  );
}
