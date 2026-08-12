"use client";

import { Badge, Button, EmptyState, Input, PageHeader, Select, Skeleton } from "@/components/ui";
import { endpoints, HqTemplate } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

export default function TemplatesPage() {
  const { can, user } = useAuth();
  const canEdit = can("settings:write") || user?.role_key === "founder";
  const qc = useQueryClient();
  const [kind, setKind] = useState("");
  const q = useQuery({
    queryKey: ["templates", kind],
    queryFn: () => endpoints.templates(kind || undefined),
  });
  const [form, setForm] = useState({ kind: "project", title: "", description: "" });

  const create = useMutation({
    mutationFn: () =>
      endpoints.createTemplate({
        kind: form.kind,
        title: form.title,
        description: form.description,
        body: { note: "Custom template" },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["templates"] });
      setForm({ kind: "project", title: "", description: "" });
      toast.success("Template created");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: (id: string) => endpoints.deleteTemplate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["templates"] });
      toast.success("Template archived");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        kicker="Library"
        title="Templates"
        description="Reusable project, task, onboarding, and doc patterns for Studio Sunny delivery."
        actions={
          <Select value={kind} onChange={(e) => setKind(e.target.value)} className="w-40">
            <option value="">All kinds</option>
            <option value="project">Project</option>
            <option value="task">Task</option>
            <option value="onboarding">Onboarding</option>
            <option value="doc">Doc</option>
          </Select>
        }
      />

      {canEdit ? (
        <form
          className="panel mb-4 grid gap-2 p-4 sm:grid-cols-4"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <Select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
            <option value="project">Project</option>
            <option value="task">Task</option>
            <option value="onboarding">Onboarding</option>
            <option value="doc">Doc</option>
          </Select>
          <Input
            placeholder="Title"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
          />
          <Input
            placeholder="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <Button type="submit" loading={create.isPending}>
            Add template
          </Button>
        </form>
      ) : null}

      {q.isLoading ? (
        <Skeleton className="h-48" />
      ) : !(q.data || []).length ? (
        <EmptyState title="No templates" body="Seeded defaults appear on first open for founders." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {(q.data || []).map((t: HqTemplate) => (
            <div key={t.id} className="panel p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <Badge>{t.kind}</Badge>
                  <p className="mt-2 text-[15px] font-semibold text-ink">{t.title}</p>
                  <p className="mt-1 text-[13px] text-muted">{t.description || "—"}</p>
                </div>
                {canEdit ? (
                  <Button variant="ghost" onClick={() => remove.mutate(t.id)} loading={remove.isPending}>
                    Archive
                  </Button>
                ) : null}
              </div>
              <pre className="mt-3 max-h-28 overflow-auto rounded-md bg-sunken/60 p-2 font-mono text-[11px] text-muted">
                {JSON.stringify(t.body, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
