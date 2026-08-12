"use client";

import { Badge, Button, EmptyState, Input, PageHeader, Select, Skeleton } from "@/components/ui";
import { endpoints, FileAsset } from "@/lib/api";
import { prettyStatus } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Download, File as FileIcon, Trash2, Upload } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import { toast } from "sonner";

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FilesPage() {
  const qc = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("");
  const [projectId, setProjectId] = useState("");
  const [dragging, setDragging] = useState(false);

  const projects = useQuery({ queryKey: ["projects"], queryFn: () => endpoints.projects() });
  const params: Record<string, string> = {};
  if (q) params.q = q;
  if (kind) params.kind = kind;
  if (projectId) params.project_id = projectId;

  const files = useQuery({
    queryKey: ["files", params],
    queryFn: () => endpoints.files(Object.keys(params).length ? params : undefined),
  });

  const upload = useMutation({
    mutationFn: (file: File) =>
      endpoints.uploadFile(file, {
        name: file.name,
        kind: kind || "asset",
        project_id: projectId || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["files"] });
      toast.success("Uploaded");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: (id: string) => endpoints.deleteFile(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["files"] });
      toast.success("File archived");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function takeFiles(list: FileList | null) {
    if (!list?.length) return;
    Array.from(list).forEach((f) => upload.mutate(f));
  }

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        kicker="Cabinet"
        title="Files"
        description="Contracts, brand packs, and delivery assets. Docs stay in Docs."
        actions={
          <>
            <Link href="/docs">
              <Button variant="outline">Docs</Button>
            </Link>
            <Link href="/vault">
              <Button variant="outline">Vault</Button>
            </Link>
            <Button onClick={() => inputRef.current?.click()} loading={upload.isPending}>
              <Upload className="size-3.5" />
              Upload
            </Button>
            <input
              ref={inputRef}
              type="file"
              className="hidden"
              multiple
              onChange={(e) => {
                takeFiles(e.target.files);
                e.target.value = "";
              }}
            />
          </>
        }
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <Input className="max-w-xs" placeholder="Search files" value={q} onChange={(e) => setQ(e.target.value)} />
        <Select className="w-40" value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">All kinds</option>
          {["asset", "contract", "brand", "deliverable", "credential"].map((k) => (
            <option key={k} value={k}>
              {prettyStatus(k)}
            </option>
          ))}
        </Select>
        <Select className="min-w-[200px] flex-1" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
          <option value="">All projects</option>
          {(projects.data || []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </Select>
      </div>

      <div
        className={`mb-5 rounded-md border border-dashed px-4 py-8 text-center transition ${
          dragging ? "border-accent bg-accent/5" : "border-line bg-sunken/30"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          takeFiles(e.dataTransfer.files);
        }}
      >
        <p className="text-[14px] text-ink">Drop files here</p>
        <p className="mt-1 text-[12px] text-muted">PDF, images, Office, zip · max 25MB</p>
      </div>

      {files.isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : !files.data?.length ? (
        <EmptyState title="No files yet" body="Upload a contract, brand pack, or project deliverable." />
      ) : (
        <ul className="divide-y divide-line border-y border-line">
          {files.data.map((f) => (
            <FileRow key={f.id} file={f} onDelete={() => remove.mutate(f.id)} deleting={remove.isPending} />
          ))}
        </ul>
      )}
    </div>
  );
}

function FileRow({
  file,
  onDelete,
  deleting,
}: {
  file: FileAsset;
  onDelete: () => void;
  deleting?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <li className="flex flex-wrap items-center gap-3 py-3">
      <span className="flex size-9 items-center justify-center rounded-md bg-sunken text-muted">
        <FileIcon className="size-4" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate text-[14px] font-semibold text-ink">{file.name}</p>
          <Badge>{prettyStatus(file.kind)}</Badge>
        </div>
        <p className="mt-0.5 text-[12px] text-muted">
          {formatBytes(file.size_bytes)} · {file.mime_type}
          {file.project_name ? ` · ${file.project_name}` : ""}
          {file.uploader_name ? ` · ${file.uploader_name}` : ""}
          {" · "}
          {format(new Date(file.created_at), "MMM d, yyyy")}
        </p>
        {file.notes ? <p className="mt-0.5 text-[12px] text-muted">{file.notes}</p> : null}
      </div>
      <div className="flex gap-1">
        <Button
          variant="ghost"
          className="h-8 px-2"
          loading={busy}
          onClick={async () => {
            try {
              setBusy(true);
              await endpoints.downloadFile(file.id, file.original_name);
            } catch (e) {
              toast.error(e instanceof Error ? e.message : "Download failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          <Download className="size-3.5" />
        </Button>
        <Button variant="ghost" className="h-8 px-2 text-danger" loading={deleting} onClick={onDelete}>
          <Trash2 className="size-3.5" />
        </Button>
      </div>
    </li>
  );
}
