"use client";

import { Badge, Button, PageHeader, Skeleton } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

export default function PermissionsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["permissions-matrix"], queryFn: endpoints.permissionsMatrix });
  const [role, setRole] = useState("developer");
  const [extras, setExtras] = useState<string[]>([]);

  useEffect(() => {
    if (q.data) {
      setExtras(q.data.overrides[role] || []);
    }
  }, [q.data, role]);

  const base = useMemo(() => new Set(q.data?.roles[role] || []), [q.data, role]);
  const overrideSet = useMemo(() => new Set(q.data?.overrides[role] || []), [q.data, role]);

  const save = useMutation({
    mutationFn: () => {
      const next = { ...(q.data?.overrides || {}) };
      next[role] = extras;
      return endpoints.updatePermissionOverrides(next);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["permissions-matrix"] });
      toast.success("Overrides saved — re-login for full effect on other sessions");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (q.isLoading || !q.data) return <Skeleton className="mx-auto h-80 max-w-5xl" />;

  const labels = q.data.labels;
  const canEdit = user?.role_key === "founder" || user?.permissions.includes("permissions:write") || user?.permissions.includes("*");

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        kicker="Access"
        title="Permissions"
        description="Server-enforced RBAC matrix. Additive overrides per role are stored on the organization."
      />

      <div className="mb-4 flex flex-wrap gap-2">
        {Object.keys(q.data.roles).map((r) => (
          <button
            key={r}
            type="button"
            onClick={() => setRole(r)}
            className={`rounded-lg border px-3 py-1.5 text-[13px] ${
              role === r ? "border-accent bg-accent/10 text-ink" : "border-line text-muted hover:text-ink"
            }`}
          >
            {labels[r] || r}
          </button>
        ))}
      </div>

      <div className="panel overflow-hidden">
        <div className="border-b border-line px-4 py-3 text-[13px]">
          <span className="font-medium text-ink">{labels[role] || role}</span>
          <span className="ml-2 text-muted">{q.data.roles[role]?.length || 0} permissions</span>
        </div>
        <div className="grid max-h-[52vh] gap-1 overflow-y-auto p-3 sm:grid-cols-2 lg:grid-cols-3">
          {q.data.all_permissions.map((perm) => {
            const fromRole = base.has(perm) && !overrideSet.has(perm);
            const fromOverride = extras.includes(perm);
            const on = fromRole || fromOverride || (role === "founder" && perm);
            return (
              <label
                key={perm}
                className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-[12px] ${
                  on ? "bg-sunken/60 text-ink" : "text-muted"
                }`}
              >
                <input
                  type="checkbox"
                  disabled={!canEdit || fromRole || role === "founder"}
                  checked={Boolean(fromRole || fromOverride)}
                  onChange={(e) => {
                    setExtras((prev) =>
                      e.target.checked ? Array.from(new Set([...prev, perm])) : prev.filter((p) => p !== perm),
                    );
                  }}
                />
                <span className="font-mono">{perm}</span>
                {fromOverride ? <Badge tone="info">extra</Badge> : null}
              </label>
            );
          })}
        </div>
        {canEdit && role !== "founder" ? (
          <div className="border-t border-line p-3">
            <Button onClick={() => save.mutate()} loading={save.isPending}>
              Save overrides for {labels[role] || role}
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
