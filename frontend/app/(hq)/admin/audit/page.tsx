"use client";

import { Badge, Button, Input, PageHeader, Select, Skeleton } from "@/components/ui";
import { AuditEntry, endpoints } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { useMemo, useState } from "react";

export default function AuditPage() {
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [limit, setLimit] = useState("80");

  const canRead =
    user?.role_key === "founder" || user?.permissions?.includes("audit:read") || user?.permissions?.includes("*");

  const params = useMemo(() => {
    const p: Record<string, string> = { limit };
    if (q.trim()) p.q = q.trim();
    if (action.trim()) p.action = action.trim();
    if (entityType) p.entity_type = entityType;
    return p;
  }, [q, action, entityType, limit]);

  const logs = useQuery({
    queryKey: ["audit", params],
    queryFn: () => endpoints.auditFiltered(params),
    enabled: !!canRead,
  });

  if (!canRead) {
    return (
      <div className="mx-auto max-w-[900px]">
        <PageHeader kicker="Admin" title="Audit logs" description="Restricted to founders and audit readers." />
        <div className="panel p-6 text-[14px] text-muted">You don’t have permission to view the audit trail.</div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        kicker="Admin"
        title="Audit logs"
        description="Append-only security and mutation trail — login, authz, creates, updates, downloads."
        actions={
          <Button variant="outline" onClick={() => logs.refetch()} loading={logs.isFetching}>
            Refresh
          </Button>
        }
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <Input className="max-w-xs" placeholder="Search action / entity" value={q} onChange={(e) => setQ(e.target.value)} />
        <Input className="max-w-[180px]" placeholder="Action contains" value={action} onChange={(e) => setAction(e.target.value)} />
        <Select className="w-44" value={entityType} onChange={(e) => setEntityType(e.target.value)}>
          <option value="">All entities</option>
          {["auth", "client", "project", "task", "document", "file", "chat", "employee", "permission"].map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
        <Select className="w-28" value={limit} onChange={(e) => setLimit(e.target.value)}>
          {["40", "80", "120", "200"].map((n) => (
            <option key={n} value={n}>
              {n} rows
            </option>
          ))}
        </Select>
      </div>

      {logs.isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      ) : !logs.data?.length ? (
        <div className="panel p-6 text-[14px] text-muted">No audit events match these filters.</div>
      ) : (
        <div className="panel overflow-hidden">
          <div className="grid grid-cols-[140px_1fr_120px_1fr] gap-2 border-b border-line px-4 py-2 text-[11px] uppercase tracking-[0.12em] text-muted max-md:hidden">
            <span>When</span>
            <span>Action</span>
            <span>Actor</span>
            <span>Detail</span>
          </div>
          <ul className="divide-y divide-line">
            {logs.data.map((row) => (
              <AuditRow key={row.id} row={row} />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function AuditRow({ row }: { row: AuditEntry }) {
  const meta = row.meta && Object.keys(row.meta).length ? JSON.stringify(row.meta) : null;
  return (
    <li className="grid grid-cols-1 gap-1 px-4 py-3 md:grid-cols-[140px_1fr_120px_1fr] md:items-start md:gap-2">
      <div className="text-[12px] text-muted">{format(new Date(row.created_at), "MMM d, HH:mm:ss")}</div>
      <div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[13px] font-medium text-ink">{row.action}</span>
          <Badge>{row.entity_type}</Badge>
        </div>
        {row.entity_id ? <p className="mt-0.5 font-mono text-[11px] text-muted">{row.entity_id}</p> : null}
      </div>
      <div className="text-[12px]">
        <p className="text-ink">{row.user_name || "System"}</p>
        <p className="text-muted">{row.user_email || row.ip_address || "—"}</p>
      </div>
      <div className="text-[12px] text-muted">
        {meta ? <p className="break-all font-mono text-[11px]">{meta}</p> : <p>—</p>}
      </div>
    </li>
  );
}
