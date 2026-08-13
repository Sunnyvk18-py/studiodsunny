"use client";

import { Badge, Button, EmptyState, PageHeader, Skeleton, healthTone } from "@/components/ui";
import { Monogram } from "@/components/monogram";
import { endpoints, Project } from "@/lib/api";
import { prettyStatus } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { LayoutGrid, List, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

export default function ProjectsPage() {
  const [view, setView] = useState<"grid" | "list">("grid");
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [archived, setArchived] = useState(false);
  const query = useQuery({
    queryKey: ["projects", archived],
    queryFn: () => endpoints.projects(archived ? { archived: "true" } : undefined),
  });

  const filtered = useMemo(() => {
    return (query.data || []).filter((p) => {
      const matchQ =
        !q ||
        p.name.toLowerCase().includes(q.toLowerCase()) ||
        (p.client_name || "").toLowerCase().includes(q.toLowerCase());
      const matchS = !status || p.status === status;
      return matchQ && matchS;
    });
  }, [query.data, q, status]);

  return (
    <div className="mx-auto max-w-[1280px]">
      <PageHeader
        kicker="Delivery"
        title="Projects"
        description="Every engagement Studio Sunny is running."
        actions={
          <>
            <Button variant={archived ? "primary" : "outline"} onClick={() => setArchived((v) => !v)}>
              {archived ? "Showing archived" : "Archived"}
            </Button>
            {!archived ? (
              <Link href="/projects/new">
                <Button>New project</Button>
              </Link>
            ) : null}
          </>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-3 size-4 text-accent" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search projects or clients"
            className="h-10 w-full rounded-xl border border-line bg-raised pl-9 pr-3 text-[13px] outline-none focus:border-accent/50"
          />
        </div>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="h-10 rounded-xl border border-line bg-raised px-3 text-[13px]"
        >
          <option value="">All statuses</option>
          {["planning", "design", "development", "testing", "client_review", "launching", "maintenance", "completed", "paused"].map(
            (s) => (
              <option key={s} value={s}>
                {prettyStatus(s)}
              </option>
            ),
          )}
        </select>
        <div className="flex h-10 rounded-xl border border-line p-1">
          <button className={`rounded-lg px-2.5 ${view === "grid" ? "bg-sunken text-ink" : "text-muted"}`} onClick={() => setView("grid")}>
            <LayoutGrid className="size-4" />
          </button>
          <button className={`rounded-lg px-2.5 ${view === "list" ? "bg-sunken text-ink" : "text-muted"}`} onClick={() => setView("list")}>
            <List className="size-4" />
          </button>
        </div>
      </div>

      {query.isLoading ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title={archived ? "No archived projects" : "No projects yet"}
          body={
            archived
              ? "Archived workspaces will show up here."
              : "Create a client first, then open a project workspace."
          }
          action={
            !archived ? (
              <Link href="/projects/new">
                <Button>Create project</Button>
              </Link>
            ) : undefined
          }
        />
      ) : view === "grid" ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((p) => (
            <ProjectCard key={p.id} project={p} archived={archived} />
          ))}
        </div>
      ) : (
        <div className="panel overflow-hidden">
          <table className="w-full text-[13px]">
            <thead className="text-left text-[11px] uppercase tracking-[0.12em] text-muted">
              <tr className="border-b border-line">
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Client</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Health</th>
                <th className="px-4 py-3">Progress</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.id} className="border-b border-line last:border-0 hover:bg-sunken/50">
                  <td className="px-4 py-3">
                    <Link href={`/projects/${p.id}`} className="font-semibold hover:text-accent">
                      {p.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted">{p.client_name}</td>
                  <td className="px-4 py-3">
                    <Badge tone={archived ? "warn" : "neutral"}>{archived ? "Archived" : prettyStatus(p.status)}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={healthTone(p.health)}>{prettyStatus(p.health)}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="progress-track w-16">
                        <div className="progress-fill" style={{ width: `${p.progress}%` }} />
                      </div>
                      <span className="tabular-nums text-muted">{p.progress}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ProjectCard({ project: p, archived }: { project: Project; archived?: boolean }) {
  return (
    <Link href={`/projects/${p.id}`} className="panel lift block p-4">
      <div className="flex items-start gap-3">
        <Monogram name={p.name} />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <p className="text-[14px] font-semibold text-ink">{p.name}</p>
            <Badge tone={archived ? "warn" : healthTone(p.health)}>
              {archived ? "Archived" : prettyStatus(p.health)}
            </Badge>
          </div>
          <p className="mt-0.5 text-[12px] text-muted">
            {p.client_name} · {p.project_type}
          </p>
        </div>
      </div>
      <div className="progress-track mt-4">
        <div className="progress-fill" style={{ width: `${p.progress}%` }} />
      </div>
      <div className="mt-2.5 flex items-center justify-between text-[12px] text-muted">
        <span>{prettyStatus(p.status)}</span>
        <span>
          {p.progress}% · {p.open_tasks || 0} open
        </span>
      </div>
    </Link>
  );
}
