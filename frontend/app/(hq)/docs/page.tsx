"use client";

import { Badge, Button, EmptyState, Input, PageHeader, Skeleton } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { prettyStatus } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { FileText } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

export default function DocsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const docs = useQuery({
    queryKey: ["docs", q],
    queryFn: () => endpoints.docs(q ? { q } : undefined),
  });

  const create = useMutation({
    mutationFn: () =>
      endpoints.createDoc({
        title: "Untitled doc",
        kind: "page",
        status: "draft",
        content: { type: "doc", content: [{ type: "paragraph" }] },
      }),
    onSuccess: (doc) => {
      qc.invalidateQueries({ queryKey: ["docs"] });
      toast.success("Doc created");
      router.push(`/docs/${doc.id}`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        kicker="Knowledge"
        title="Docs"
        description="Briefs, SOPs, and decisions — written where the work lives."
        actions={
          <Button onClick={() => create.mutate()} loading={create.isPending}>
            New doc
          </Button>
        }
      />

      <div className="mb-4">
        <Input
          placeholder="Search docs"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-sm"
        />
      </div>

      {docs.isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      ) : !docs.data?.length ? (
        <EmptyState
          title="No documents yet"
          body="Create a brief, handbook page, or meeting note."
          action={
            <Button onClick={() => create.mutate()} loading={create.isPending}>
              New doc
            </Button>
          }
        />
      ) : (
        <ul className="divide-y divide-line border-y border-line">
          {docs.data.map((d) => (
            <li key={d.id}>
              <Link
                href={`/docs/${d.id}`}
                className="flex items-start gap-3 py-4 transition hover:bg-sunken/40"
              >
                <span className="mt-0.5 flex size-9 items-center justify-center rounded-md bg-sunken text-muted">
                  <FileText className="size-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-[15px] font-semibold text-ink">{d.title}</p>
                    <Badge>{prettyStatus(d.kind)}</Badge>
                    <Badge tone={d.status === "published" ? "ok" : "neutral"}>{prettyStatus(d.status)}</Badge>
                  </div>
                  <p className="mt-1 line-clamp-1 text-[13px] text-muted">
                    {d.summary || d.project_name || d.client_name || "Company doc"}
                  </p>
                  <p className="mt-1 text-[12px] text-muted">
                    {d.author_name || "HQ"} · updated {format(new Date(d.updated_at), "MMM d, HH:mm")}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
