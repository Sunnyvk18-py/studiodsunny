"use client";

import { Badge, Button, EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { Monogram } from "@/components/monogram";
import { endpoints } from "@/lib/api";
import { formatINR, prettyStatus } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

export default function ClientsPage() {
  const [q, setQ] = useState("");
  const [archived, setArchived] = useState(false);
  const query = useQuery({
    queryKey: ["clients", q, archived],
    queryFn: () => endpoints.clients({ q: q || undefined, archived }),
  });

  return (
    <div className="mx-auto max-w-[1200px]">
      <PageHeader
        kicker="Relationships"
        title="Clients"
        description="The companies Studio Sunny is building for."
        actions={
          <>
            <Button variant={archived ? "primary" : "outline"} onClick={() => setArchived((v) => !v)}>
              {archived ? "Showing archived" : "Archived"}
            </Button>
            {!archived ? (
              <Link href="/clients/new">
                <Button>Add client</Button>
              </Link>
            ) : null}
          </>
        }
      />
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search clients"
        className="mb-5 h-10 w-full max-w-md rounded-xl border border-line bg-raised px-3 text-[13px] outline-none focus:border-accent/50"
      />
      {query.isLoading ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-36" />
          ))}
        </div>
      ) : !query.data?.length ? (
        <EmptyState
          title={archived ? "No archived clients" : "No clients yet"}
          body={
            archived
              ? "Archived accounts will show up here."
              : "Add Muttonly, Patel Gems, or a new account to start the delivery workflow."
          }
          action={
            !archived ? (
              <Link href="/clients/new">
                <Button>Add client</Button>
              </Link>
            ) : undefined
          }
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {query.data.map((c) => (
            <Link key={c.id} href={`/clients/${c.id}`} className="panel lift block p-4">
              <div className="flex items-start gap-3">
                <Monogram name={c.business_name} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-semibold">{c.business_name}</p>
                    <Badge tone={archived ? "warn" : "ok"}>{archived ? "Archived" : prettyStatus(c.status)}</Badge>
                  </div>
                  <p className="mt-0.5 text-[12px] text-muted">
                    {c.industry || "—"} · {c.location || "—"}
                  </p>
                </div>
              </div>
              <div className="mt-4 flex justify-between text-[12px] text-muted">
                <span>{c.active_projects || 0} active projects</span>
                <span>{c.primary_contact_name}</span>
              </div>
              {c.pending_invoices ? (
                <p className="mt-2 text-[12px] font-semibold text-warn">
                  Outstanding {formatINR(Number(c.pending_invoices))}
                </p>
              ) : null}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
