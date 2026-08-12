"use client";

import { Badge, Button, EmptyState, Input, PageHeader, Skeleton } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { prettyStatus } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Download, KeyRound, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function VaultPage() {
  const { can } = useAuth();
  const qc = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState("");
  const [notes, setNotes] = useState("");

  const canRead = can("credentials:read");
  const canWrite = can("credentials:write");

  const files = useQuery({
    queryKey: ["files", "credential", q],
    queryFn: () => endpoints.files({ kind: "credential", ...(q ? { q } : {}) }),
    enabled: canRead,
  });

  const upload = useMutation({
    mutationFn: (file: File) =>
      endpoints.uploadFile(file, {
        name: file.name,
        kind: "credential",
        notes: notes || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["files"] });
      setNotes("");
      toast.success("Credential stored");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: (id: string) => endpoints.deleteFile(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["files"] });
      toast.success("Removed from vault");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (!canRead) {
    return (
      <EmptyState
        title="Credential vault is restricted"
        body="Only founder (and roles with credentials:read) can open the vault."
      />
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        kicker="Security"
        title="Credential vault"
        description="API keys, certs, and sensitive files. Downloads are audited. Never paste secrets into chat."
        actions={
          canWrite ? (
            <Button onClick={() => inputRef.current?.click()} loading={upload.isPending}>
              <Upload className="size-3.5" />
              Add secret file
            </Button>
          ) : null
        }
      />

      <input
        ref={inputRef}
        type="file"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) upload.mutate(f);
          e.target.value = "";
        }}
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <Input className="max-w-xs" placeholder="Search vault…" value={q} onChange={(e) => setQ(e.target.value)} />
        {canWrite ? (
          <Input
            className="max-w-sm"
            placeholder="Optional notes for next upload"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        ) : null}
      </div>

      {files.isLoading ? (
        <Skeleton className="h-48" />
      ) : !(files.data || []).length ? (
        <EmptyState title="Vault is empty" body="Upload env packs, PEM files, or client credential PDFs." />
      ) : (
        <div className="panel divide-y divide-line">
          {(files.data || []).map((f) => (
            <div key={f.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
              <span className="grid size-9 place-items-center rounded-lg bg-sunken text-accent">
                <KeyRound className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[14px] font-medium text-ink">{f.name}</p>
                <p className="text-[12px] text-muted">
                  {formatBytes(f.size_bytes)} · {prettyStatus(f.mime_type)} ·{" "}
                  {format(new Date(f.created_at), "MMM d, yyyy")}
                  {f.notes ? ` · ${f.notes}` : ""}
                </p>
              </div>
              <Badge tone="warn">credential</Badge>
              <Button
                variant="ghost"
                onClick={() => endpoints.downloadFile(f.id, f.original_name || f.name).catch((e) => toast.error(e.message))}
              >
                <Download className="size-3.5" />
              </Button>
              {canWrite ? (
                <Button variant="ghost" onClick={() => remove.mutate(f.id)}>
                  <Trash2 className="size-3.5" />
                </Button>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
