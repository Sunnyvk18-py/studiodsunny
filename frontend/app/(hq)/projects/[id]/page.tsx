"use client";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { TaskDetailDrawer } from "@/components/task-detail-drawer";
import { Avatar, Badge, Button, Input, PageHeader, Select, Skeleton, Textarea, healthTone, priorityTone } from "@/components/ui";
import { endpoints, Task } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { prettyStatus } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Suspense, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

const TABS = ["Overview", "Tasks", "Docs", "Files", "Timeline", "Team", "Activity"] as const;
const PROJECT_STATUSES = [
  "planning",
  "design",
  "development",
  "testing",
  "client_review",
  "launching",
  "maintenance",
  "completed",
  "paused",
];

export default function ProjectWorkspacePage() {
  return (
    <Suspense fallback={<Skeleton className="h-64" />}>
      <ProjectWorkspace />
    </Suspense>
  );
}

function ProjectWorkspace() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const qc = useQueryClient();
  const { can } = useAuth();
  const canWrite = can("projects:write");
  const openTaskId = searchParams.get("task");
  const [tab, setTab] = useState<(typeof TABS)[number]>(openTaskId ? "Tasks" : "Overview");
  const [editing, setEditing] = useState(false);
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    status: "planning",
    start_date: "",
    target_completion_date: "",
  });
  const project = useQuery({ queryKey: ["project", id], queryFn: () => endpoints.project(id) });
  const tasks = useQuery({ queryKey: ["tasks", id], queryFn: () => endpoints.tasks({ project_id: id }) });
  const activity = useQuery({ queryKey: ["activity", id], queryFn: () => endpoints.activity(id) });

  useEffect(() => {
    if (openTaskId) setTab("Tasks");
  }, [openTaskId]);

  function setTaskParam(taskId: string | null) {
    const sp = new URLSearchParams(searchParams.toString());
    if (taskId) sp.set("task", taskId);
    else sp.delete("task");
    const qs = sp.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  useEffect(() => {
    if (!project.data) return;
    setForm({
      name: project.data.name,
      description: project.data.description || "",
      status: project.data.status,
      start_date: project.data.start_date || "",
      target_completion_date: project.data.target_completion_date || "",
    });
  }, [project.data]);

  const save = useMutation({
    mutationFn: () =>
      endpoints.updateProject(id, {
        name: form.name,
        description: form.description || null,
        status: form.status,
        start_date: form.start_date || null,
        target_completion_date: form.target_completion_date || null,
      }),
    onSuccess: (updated) => {
      qc.setQueryData(["project", id], updated);
      qc.invalidateQueries({ queryKey: ["projects"] });
      setEditing(false);
      toast.success("Project updated");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const archive = useMutation({
    mutationFn: () => endpoints.archiveProject(id),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ["projects"] });
      const previous = qc.getQueriesData({ queryKey: ["projects"] });
      qc.setQueriesData({ queryKey: ["projects"] }, (old: unknown) => {
        if (!Array.isArray(old)) return old;
        return old.filter((p: { id: string }) => p.id !== id);
      });
      return { previous };
    },
    onError: (e: Error, _v, ctx) => {
      ctx?.previous?.forEach(([key, data]) => qc.setQueryData(key, data));
      toast.error(e.message);
    },
    onSuccess: () => {
      toast.success("Project archived");
      router.push("/projects");
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });

  if (project.isLoading || !project.data) {
    return <Skeleton className="h-64" />;
  }

  const p = project.data;
  const archived = Boolean(p.archived);

  return (
    <div className="mx-auto max-w-[1200px]">
      <PageHeader
        kicker={p.client_name || "Project"}
        title={p.name}
        description={p.description || p.project_type}
        actions={
          <>
            {archived ? <Badge tone="warn">Archived</Badge> : null}
            <Badge tone={healthTone(p.health)}>{prettyStatus(p.health)}</Badge>
            <Badge>{prettyStatus(p.status)}</Badge>
            {!archived && canWrite ? (
              <>
                <Button variant="outline" onClick={() => setEditing((v) => !v)}>
                  {editing ? "Cancel edit" : "Edit"}
                </Button>
                <Button variant="outline" onClick={() => setConfirmArchive(true)}>
                  Archive
                </Button>
              </>
            ) : null}
          </>
        }
      />

      {editing && !archived ? (
        <form
          className="panel mb-6 space-y-4 p-5"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block sm:col-span-2">
              <span className="mb-1.5 block text-xs font-medium text-muted">Name</span>
              <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1.5 block text-xs font-medium text-muted">Description</span>
              <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-muted">Status</span>
              <Select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                {PROJECT_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {prettyStatus(s)}
                  </option>
                ))}
              </Select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-muted">Start date</span>
              <Input
                type="date"
                value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-muted">Target completion</span>
              <Input
                type="date"
                value={form.target_completion_date}
                onChange={(e) => setForm({ ...form, target_completion_date: e.target.value })}
              />
            </label>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={save.isPending}>
              Save changes
            </Button>
          </div>
        </form>
      ) : null}

      <div className="mb-6 flex gap-1 overflow-x-auto border-b border-line">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-[13px] font-medium ${tab === t ? "border-b-2 border-accent text-ink" : "text-muted hover:text-ink"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Overview" && (
        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4">
            <div className="panel p-5">
              <div className="mb-4 flex items-end justify-between">
                <div>
                  <p className="text-[12px] text-muted">Progress</p>
                  <p className="gold-num mt-1 text-[28px] font-semibold">{p.progress}%</p>
                </div>
                <Badge tone={healthTone(p.health)}>{prettyStatus(p.health)}</Badge>
              </div>
              <div className="progress-track h-1.5">
                <div className="progress-fill" style={{ width: `${p.progress}%` }} />
              </div>
              <div className="mt-5 grid gap-4 sm:grid-cols-3">
                <Stat label="Phase" value={prettyStatus(p.status)} />
                <Stat label="Deadline" value={p.target_completion_date ? format(new Date(p.target_completion_date), "MMM d, yyyy") : "—"} />
                <Stat label="Open tasks" value={String(p.open_tasks ?? tasks.data?.filter((t) => t.status !== "completed").length ?? 0)} />
                <Stat label="Blocked" value={String(p.blocked_tasks ?? 0)} />
                <Stat label="Hours spent" value={String(p.hours_spent)} />
              </div>
            </div>
            <div className="panel p-5">
              <p className="kicker mb-3">Next milestone</p>
              {p.milestones[0] ? (
                <div>
                  <p className="font-medium">{p.milestones.find((m) => m.status !== "completed")?.title || p.milestones.at(-1)?.title}</p>
                  <p className="mt-1 text-sm text-muted">
                    {prettyStatus(p.milestones.find((m) => m.status !== "completed")?.status || "")}
                  </p>
                </div>
              ) : (
                <CreateMilestone projectId={id} />
              )}
            </div>
          </div>
          <div className="panel p-5">
            <p className="kicker mb-3">Team</p>
            <ul className="space-y-3">
              {p.members.map((m) => (
                <li key={m.id} className="flex items-center gap-3">
                  <Avatar name={m.user?.display_name || "?"} />
                  <div>
                    <p className="text-sm">{m.user?.display_name}</p>
                    <p className="text-xs text-muted">{prettyStatus(m.role_on_project)}</p>
                  </div>
                </li>
              ))}
            </ul>
            {p.tech_stack?.length ? (
              <div className="mt-6 flex flex-wrap gap-1.5">
                {p.tech_stack.map((t) => (
                  <Badge key={t}>{t}</Badge>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      )}

      {tab === "Tasks" && (
        <TasksPanel projectId={id} tasks={tasks.data || []} onOpenTask={(taskId) => setTaskParam(taskId)} />
      )}

      {tab === "Docs" && <ProjectDocs projectId={id} />}

      {tab === "Files" && <ProjectFiles projectId={id} />}

      {tab === "Timeline" && (
        <div className="panel p-6">
          <ol className="relative ml-3 border-l border-line">
            {(p.milestones.length ? p.milestones : []).map((m) => (
              <li key={m.id} className="mb-6 ml-6">
                <span className={`absolute -left-1.5 mt-1.5 size-3 rounded-full ${m.status === "completed" ? "bg-ok" : m.status === "in_progress" ? "bg-accent" : "bg-sunken"}`} />
                <p className="font-medium">{m.title}</p>
                <p className="text-xs text-muted">
                  {prettyStatus(m.status)}
                  {m.due_date ? ` · ${format(new Date(m.due_date), "MMM d")}` : ""}
                </p>
              </li>
            ))}
          </ol>
          <CreateMilestone projectId={id} />
        </div>
      )}

      {tab === "Team" && (
        <div className="grid gap-3 md:grid-cols-2">
          {p.members.map((m) => (
            <div key={m.id} className="panel lift flex items-center gap-3 p-4">
              <Avatar name={m.user?.display_name || "?"} size={44} />
              <div>
                <p className="font-medium">{m.user?.display_name}</p>
                <p className="text-xs text-muted">{prettyStatus(m.role_on_project)}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "Activity" && (
        <div className="panel p-5">
          <ul className="space-y-3">
            {(activity.data || []).map((a) => (
              <li key={a.id} className="text-sm">
                <span className="text-ink">{a.summary}</span>
                <span className="ml-2 text-xs text-muted">{format(new Date(a.created_at), "MMM d, HH:mm")}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <ConfirmDialog
        open={confirmArchive}
        title={`Archive ${p.name}?`}
        body="It will leave the default project list. You can find it again with the Archived filter."
        confirmLabel="Archive"
        loading={archive.isPending}
        onCancel={() => setConfirmArchive(false)}
        onConfirm={() => archive.mutate()}
      />

      {openTaskId ? <TaskDetailDrawer taskId={openTaskId} onClose={() => setTaskParam(null)} /> : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-[20px] font-semibold tabular-nums tracking-tight capitalize">{value}</p>
    </div>
  );
}

function CreateMilestone({ projectId }: { projectId: string }) {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [phase, setPhase] = useState("development");
  const mut = useMutation({
    mutationFn: () => endpoints.createMilestone(projectId, { title, phase, status: "upcoming" }),
    onSuccess: () => {
      setTitle("");
      qc.invalidateQueries({ queryKey: ["project", projectId] });
      qc.invalidateQueries({ queryKey: ["activity"] });
      toast.success("Milestone added");
    },
    onError: (e: Error) => toast.error(e.message),
  });
  return (
    <form
      className="mt-4 flex flex-wrap gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (!title.trim()) return;
        mut.mutate();
      }}
    >
      <Input className="max-w-xs" placeholder="Milestone title" value={title} onChange={(e) => setTitle(e.target.value)} />
      <Select className="max-w-[160px]" value={phase} onChange={(e) => setPhase(e.target.value)}>
        {["discovery", "planning", "design", "development", "testing", "client_review", "deployment", "launch", "maintenance"].map((p) => (
          <option key={p} value={p}>
            {prettyStatus(p)}
          </option>
        ))}
      </Select>
      <Button type="submit" loading={mut.isPending}>
        Add milestone
      </Button>
    </form>
  );
}

function ProjectFiles({ projectId }: { projectId: string }) {
  const qc = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const files = useQuery({
    queryKey: ["files", "project", projectId],
    queryFn: () => endpoints.files({ project_id: projectId }),
  });
  const upload = useMutation({
    mutationFn: (file: File) =>
      endpoints.uploadFile(file, {
        name: file.name,
        kind: "deliverable",
        project_id: projectId,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["files"] });
      toast.success("Uploaded to project");
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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[13px] text-muted">Files attached to this project.</p>
        <Button onClick={() => inputRef.current?.click()} loading={upload.isPending}>
          Upload
        </Button>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          multiple
          onChange={(e) => {
            const list = e.target.files;
            if (list) Array.from(list).forEach((f) => upload.mutate(f));
            e.target.value = "";
          }}
        />
      </div>
      {files.isLoading ? (
        <Skeleton className="h-24" />
      ) : !files.data?.length ? (
        <p className="text-[13px] text-muted">No project files yet.</p>
      ) : (
        <ul className="divide-y divide-line border-y border-line">
          {files.data.map((f) => (
            <li key={f.id} className="flex items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="truncate text-[14px] font-medium">{f.name}</p>
                <p className="text-[12px] text-muted">
                  {prettyStatus(f.kind)} · {(f.size_bytes / 1024).toFixed(1)} KB · {format(new Date(f.created_at), "MMM d")}
                </p>
              </div>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  className="h-8 px-2 text-[12px]"
                  onClick={() =>
                    endpoints.downloadFile(f.id, f.original_name).catch((e: Error) => toast.error(e.message))
                  }
                >
                  Download
                </Button>
                <Button variant="ghost" className="h-8 px-2 text-[12px] text-danger" onClick={() => remove.mutate(f.id)}>
                  Archive
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ProjectDocs({ projectId }: { projectId: string }) {
  const router = useRouter();
  const qc = useQueryClient();
  const docs = useQuery({
    queryKey: ["docs", "project", projectId],
    queryFn: () => endpoints.docs({ project_id: projectId }),
  });
  const create = useMutation({
    mutationFn: () =>
      endpoints.createDoc({
        title: "Project brief",
        kind: "brief",
        status: "draft",
        project_id: projectId,
        content: { type: "doc", content: [{ type: "paragraph" }] },
      }),
    onSuccess: (doc) => {
      qc.invalidateQueries({ queryKey: ["docs"] });
      router.push(`/docs/${doc.id}`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-[13px] text-muted">Docs attached to this project.</p>
        <Button onClick={() => create.mutate()} loading={create.isPending}>
          New project doc
        </Button>
      </div>
      {docs.isLoading ? (
        <Skeleton className="h-24" />
      ) : !docs.data?.length ? (
        <p className="text-[13px] text-muted">No docs yet. Start a brief or decision log.</p>
      ) : (
        <ul className="divide-y divide-line border-y border-line">
          {docs.data.map((d) => (
            <li key={d.id}>
              <Link href={`/docs/${d.id}`} className="flex items-center justify-between py-3 hover:bg-sunken/40">
                <div>
                  <p className="text-[14px] font-medium">{d.title}</p>
                  <p className="text-[12px] text-muted">
                    {prettyStatus(d.kind)} · {prettyStatus(d.status)} · {format(new Date(d.updated_at), "MMM d")}
                  </p>
                </div>
                <span className="text-[12px] text-muted">Open →</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TasksPanel({
  projectId,
  tasks,
  onOpenTask,
}: {
  projectId: string;
  tasks: Task[];
  onOpenTask: (taskId: string) => void;
}) {
  const qc = useQueryClient();
  const people = useQuery({ queryKey: ["employees"], queryFn: () => endpoints.employees() });
  const [title, setTitle] = useState("");
  const [assignee, setAssignee] = useState("");
  const [priority, setPriority] = useState("medium");

  const create = useMutation({
    mutationFn: () =>
      endpoints.createTask({
        title,
        project_id: projectId,
        assignee_id: assignee || null,
        priority,
        status: "todo",
      }),
    onSuccess: () => {
      setTitle("");
      qc.invalidateQueries({ queryKey: ["tasks", projectId] });
      qc.invalidateQueries({ queryKey: ["project", projectId] });
      qc.invalidateQueries({ queryKey: ["desk"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["notifications"] });
      toast.success("Task created");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const update = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => endpoints.updateTask(id, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks", projectId] });
      qc.invalidateQueries({ queryKey: ["project", projectId] });
      qc.invalidateQueries({ queryKey: ["desk"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Updated");
    },
  });

  const columns = ["backlog", "todo", "in_progress", "review", "blocked", "completed"];

  return (
    <div>
      <form
        className="mb-5 flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (!title.trim()) return;
          create.mutate();
        }}
      >
        <Input className="min-w-[220px] flex-1" placeholder="New task" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Select className="w-48" value={assignee} onChange={(e) => setAssignee(e.target.value)}>
          <option value="">Unassigned</option>
          {(people.data || []).map((e) => (
            <option key={e.user_id} value={e.user_id}>
              {e.display_name}
            </option>
          ))}
        </Select>
        <Select className="w-32" value={priority} onChange={(e) => setPriority(e.target.value)}>
          {["low", "medium", "high", "urgent"].map((p) => (
            <option key={p}>{p}</option>
          ))}
        </Select>
        <Button type="submit" loading={create.isPending}>
          Add task
        </Button>
      </form>

      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        {columns.map((col) => (
          <div key={col} className="rounded-2xl border border-line bg-sunken/50 p-3">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">{prettyStatus(col)}</p>
              <span className="gold-num text-[12px] font-semibold">{tasks.filter((t) => t.status === col).length}</span>
            </div>
            <div className="space-y-2">
              {tasks
                .filter((t) => t.status === col)
                .map((t) => (
                  <div
                    key={t.id}
                    className="panel lift cursor-pointer p-3"
                    onClick={() => onOpenTask(t.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onOpenTask(t.id);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                  >
                    <p className="text-sm font-medium">{t.title}</p>
                    <p className="mt-1 text-[11px] text-muted">{t.assignee_name || "Unassigned"}</p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      <Badge tone={priorityTone(t.priority)}>{t.priority}</Badge>
                    </div>
                    <select
                      className="mt-2 w-full rounded-lg border border-line bg-bg px-2 py-1 text-xs"
                      value={t.status}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => update.mutate({ id: t.id, status: e.target.value })}
                    >
                      {columns.map((s) => (
                        <option key={s} value={s}>
                          {prettyStatus(s)}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
