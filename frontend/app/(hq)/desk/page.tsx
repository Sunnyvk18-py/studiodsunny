"use client";

import { Badge, Button, PageHeader, Skeleton, priorityTone } from "@/components/ui";
import { Desk, Task, endpoints } from "@/lib/api";
import { prettyStatus } from "@/lib/utils";
import { deskQuery } from "@/lib/query";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import Link from "next/link";
import { toast } from "sonner";

const STATUS_ACTIONS: { label: string; status: string }[] = [
  { label: "Start work", status: "in_progress" },
  { label: "Blocked", status: "blocked" },
  { label: "Completed", status: "completed" },
];

function TaskRow({
  task,
  onStatus,
  index,
}: {
  task: Task;
  onStatus: (id: string, status: string) => void;
  index?: number;
}) {
  return (
    <div className="panel lift p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex gap-3">
          {index != null ? (
            <span className="gold-num pt-0.5 text-[15px] font-semibold">{String(index + 1).padStart(2, "0")}</span>
          ) : null}
          <div>
            <p className="text-[14px] font-semibold text-ink">{task.title}</p>
            <p className="mt-1 text-[12px] text-muted">
              {task.project_name || "No project"}
              {task.due_date ? ` · due ${format(new Date(task.due_date), "MMM d")}` : ""}
            </p>
          </div>
        </div>
        <div className="flex gap-1.5">
          <Badge tone={priorityTone(task.priority)}>{task.priority}</Badge>
          <Badge>{prettyStatus(task.status)}</Badge>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {STATUS_ACTIONS.map((a) => (
          <Button
            key={a.label}
            variant={a.status === "completed" ? "primary" : "outline"}
            className="h-8 px-2.5 text-[12px]"
            onClick={() => onStatus(task.id, a.status)}
          >
            {a.label}
          </Button>
        ))}
      </div>
    </div>
  );
}

export default function DeskPage() {
  const qc = useQueryClient();
  const q = useQuery(deskQuery);
  const update = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => endpoints.updateTask(id, { status }),
    onMutate: async ({ id, status }) => {
      await qc.cancelQueries({ queryKey: ["desk"] });
      const previous = qc.getQueryData<Desk>(["desk"]);
      qc.setQueryData<Desk>(["desk"], (desk) => {
        if (!desk) return desk;
        const patch = (list: Task[]) => list.map((t) => (t.id === id ? { ...t, status } : t));
        return { ...desk, focus: patch(desk.focus), due_today: patch(desk.due_today), blocked: patch(desk.blocked) };
      });
      return { previous };
    },
    onError: (e: Error, _vars, ctx) => {
      if (ctx?.previous) qc.setQueryData(["desk"], ctx.previous);
      toast.error(e.message);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["desk"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.invalidateQueries({ queryKey: ["notifications"] });
    },
    onSuccess: () => toast.success("Task updated"),
  });

  if (q.isLoading || !q.data) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-56" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  const desk = q.data;

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader kicker="Personal" title="My Desk" description="Your day, focus list, and assigned work." />

      <section className="mb-6">
        <h2 className="section-title mb-3">Focus</h2>
        <div className="grid gap-3">
          {desk.focus.length === 0 ? (
            <p className="text-[13px] text-muted">No open tasks assigned to you.</p>
          ) : (
            desk.focus.map((t, i) => (
              <TaskRow key={t.id} index={i} task={t} onStatus={(id, status) => update.mutate({ id, status })} />
            ))
          )}
        </div>
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <section>
          <h2 className="section-title mb-3">Due today</h2>
          <div className="space-y-3">
            {desk.due_today.length === 0 ? <p className="text-[13px] text-muted">Nothing due today.</p> : null}
            {desk.due_today.map((t) => (
              <TaskRow key={t.id} task={t} onStatus={(id, status) => update.mutate({ id, status })} />
            ))}
          </div>
        </section>
        <section>
          <h2 className="section-title mb-3">Blocked</h2>
          <div className="space-y-3">
            {desk.blocked.length === 0 ? <p className="text-[13px] text-muted">No blockers.</p> : null}
            {desk.blocked.map((t) => (
              <TaskRow key={t.id} task={t} onStatus={(id, status) => update.mutate({ id, status })} />
            ))}
          </div>
        </section>
      </div>

      <section className="mt-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="section-title">Assigned projects</h2>
          <Link href="/projects" className="text-[12px] font-semibold text-accent hover:underline">
            All projects
          </Link>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {desk.projects.map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`} className="panel lift p-4">
              <div className="flex items-center justify-between gap-2">
                <p className="font-semibold">{p.name}</p>
                <Badge>{prettyStatus(p.status)}</Badge>
              </div>
              <p className="mt-1 text-[12px] text-muted">{p.client_name}</p>
              <div className="progress-track mt-3">
                <div className="progress-fill" style={{ width: `${p.progress}%` }} />
              </div>
              <p className="mt-2 text-[12px] text-muted">{p.progress}% complete</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
