"use client";

import { Badge, EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { formatINR, prettyStatus } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";

export default function FinancePage() {
  const q = useQuery({ queryKey: ["invoices"], queryFn: endpoints.invoices });
  const invoices = q.data || [];
  const paid = invoices.filter((i) => i.status === "paid").reduce((s, i) => s + Number(i.amount), 0);
  const outstanding = invoices
    .filter((i) => ["sent", "viewed", "partial", "overdue"].includes(i.status))
    .reduce((s, i) => s + Number(i.amount), 0);
  const overdue = invoices.filter((i) => i.status === "overdue").reduce((s, i) => s + Number(i.amount), 0);

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader kicker="Commercial" title="Finance" description="Invoices, outstanding balances, and monthly revenue." />
      {q.isError ? (
        <EmptyState title="Finance is restricted" body="Only founder, finance, and authorized operators can see invoices." />
      ) : q.isLoading ? (
        <Skeleton className="h-64" />
      ) : (
        <>
          <div className="mb-4 grid gap-3 sm:grid-cols-3">
            <div className="panel p-4">
              <p className="text-[12px] text-muted">Collected</p>
              <p className="mt-1 text-[24px] font-semibold tabular-nums text-ok">{formatINR(paid)}</p>
            </div>
            <div className="panel p-4">
              <p className="text-[12px] text-muted">Outstanding</p>
              <p className="mt-1 text-[24px] font-semibold tabular-nums text-warn">{formatINR(outstanding)}</p>
            </div>
            <div className="panel p-4">
              <p className="text-[12px] text-muted">Overdue</p>
              <p className="mt-1 text-[24px] font-semibold tabular-nums text-danger">{formatINR(overdue)}</p>
            </div>
          </div>
          <div className="panel overflow-hidden">
            <table className="w-full text-[13px]">
              <thead className="text-left text-[11px] uppercase tracking-[0.12em] text-muted">
                <tr className="border-b border-line">
                  <th className="px-4 py-3">Invoice</th>
                  <th className="px-4 py-3">Client</th>
                  <th className="px-4 py-3">Amount</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Due</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr key={inv.id} className="border-b border-line last:border-0 hover:bg-sunken/40">
                    <td className="px-4 py-3 font-semibold">{inv.number}</td>
                    <td className="px-4 py-3 text-muted">{inv.client_name}</td>
                    <td className="px-4 py-3 tabular-nums">
                      {inv.currency === "USD" ? `$${Number(inv.amount).toLocaleString()}` : formatINR(Number(inv.amount))}
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={inv.status === "paid" ? "ok" : inv.status === "overdue" ? "danger" : "warn"}>
                        {prettyStatus(inv.status)}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-muted">{inv.due_date || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
