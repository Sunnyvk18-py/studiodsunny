"use client";

import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  PointerSensor,
  closestCorners,
  useDroppable,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Badge, Button, Input, PageHeader, Select, Skeleton, priorityTone } from "@/components/ui";
import { Task, endpoints } from "@/lib/api";
import { prettyStatus } from "@/lib/utils";
import { tasksQuery } from "@/lib/query";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useOptimistic, useState, useTransition } from "react";
import { toast } from "sonner";

const COLUMNS = ["backlog", "todo", "in_progress", "review", "blocked", "completed"] as const;

export default function TasksPage() {
  return (
    <Suspense>
      <TasksInner />
    </Suspense>
  );
}

function TasksInner() {
  const params = useSearchParams();
  const qc = useQueryClient();
  const [mine, setMine] = useState(false);
  const [title, setTitle] = useState("");
  const [projectId, setProjectId] = useState("");
  const [assignee, setAssignee] = useState("");
  const [showNew, setShowNew] = useState(params.get("new") === "1");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [, startTransition] = useTransition();

  const tasks = useQuery(tasksQuery(mine));
  const projects = useQuery({ queryKey: ["projects"], queryFn: () => endpoints.projects() });
  const people = useQuery({ queryKey: ["employees"], queryFn: () => endpoints.employees() });
  const [optimisticTasks, applyOptimistic] = useOptimistic(
    tasks.data || [],
    (state: Task[], next: { id: string; status: string }) =>
      state.map((t) => (t.id === next.id ? { ...t, status: next.status } : t)),
  );

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  const create = useMutation({
    mutationFn: () =>
      endpoints.createTask({
        title,
        project_id: projectId || null,
        assignee_id: assignee || null,
        status: "todo",
        priority: "medium",
      }),
    onSuccess: () => {
      setTitle("");
      setShowNew(false);
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.invalidateQueries({ queryKey: ["desk"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["calendar"] });
      toast.success("Task created");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const update = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => endpoints.updateTask(id, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.invalidateQueries({ queryKey: ["desk"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["calendar"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const grouped = useMemo(() => {
    return COLUMNS.map((col) => ({ col, items: optimisticTasks.filter((t) => t.status === col) }));
  }, [optimisticTasks]);

  const activeTask = optimisticTasks.find((t) => t.id === activeId) || null;

  function moveTask(id: string, status: string) {
    const current = optimisticTasks.find((t) => t.id === id);
    if (!current || current.status === status) return;
    startTransition(() => {
      applyOptimistic({ id, status });
      update.mutate({ id, status });
    });
  }

  function onDragEnd(event: DragEndEvent) {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;
    const taskId = String(active.id);
    const overId = String(over.id);
    const overColumn = COLUMNS.includes(overId as (typeof COLUMNS)[number])
      ? overId
      : optimisticTasks.find((t) => t.id === overId)?.status;
    if (overColumn) moveTask(taskId, overColumn);
  }

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        kicker="Work"
        title="Tasks"
        description="Drag cards across columns. Status still updates optimistically."
        actions={
          <>
            <Button variant={mine ? "primary" : "outline"} onClick={() => setMine((v) => !v)}>
              {mine ? "Showing mine" : "Assigned to me"}
            </Button>
            <Button onClick={() => setShowNew((v) => !v)}>New task</Button>
          </>
        }
      />

      {showNew ? (
        <form
          className="panel mb-6 flex flex-wrap gap-2 p-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (!title.trim()) return;
            create.mutate();
          }}
        >
          <Input className="min-w-[200px] flex-1" placeholder="Task title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <Select className="w-52" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">No project</option>
            {(projects.data || []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </Select>
          <Select className="w-48" value={assignee} onChange={(e) => setAssignee(e.target.value)}>
            <option value="">Unassigned</option>
            {(people.data || []).map((e) => (
              <option key={e.user_id} value={e.user_id}>
                {e.display_name}
              </option>
            ))}
          </Select>
          <Button type="submit" loading={create.isPending}>
            Create
          </Button>
        </form>
      ) : null}

      {tasks.isLoading ? (
        <Skeleton className="h-64" />
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={(e) => setActiveId(String(e.active.id))}
          onDragEnd={onDragEnd}
          onDragCancel={() => setActiveId(null)}
        >
          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
            {grouped.map((g) => (
              <TaskColumn key={g.col} col={g.col} items={g.items} onStatus={moveTask} />
            ))}
          </div>
          <DragOverlay>
            {activeTask ? (
              <div className="panel p-3 shadow-lg">
                <p className="text-[13px] font-semibold">{activeTask.title}</p>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      )}
    </div>
  );
}

function TaskColumn({
  col,
  items,
  onStatus,
}: {
  col: string;
  items: Task[];
  onStatus: (id: string, status: string) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: col });

  return (
    <div
      ref={setNodeRef}
      className={`rounded-2xl border border-line bg-sunken/40 p-3 transition ${isOver ? "border-accent bg-accent/5" : ""}`}
    >
      <div className="mb-3 flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">{prettyStatus(col)}</p>
        <span className="gold-num text-[12px] font-semibold">{items.length}</span>
      </div>
      <SortableContext items={items.map((t) => t.id)} strategy={verticalListSortingStrategy}>
        <div className="scroll-thin max-h-[70vh] space-y-2 overflow-y-auto">
          {items.map((t) => (
            <SortableTask key={t.id} task={t} onStatus={onStatus} />
          ))}
        </div>
      </SortableContext>
    </div>
  );
}

function SortableTask({ task, onStatus }: { task: Task; onStatus: (id: string, status: string) => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: task.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="panel lift p-3" {...attributes} {...listeners}>
      <p className="text-[13px] font-semibold">{task.title}</p>
      <p className="mt-1 text-[11px] text-muted">
        {task.project_name || "No project"} · {task.assignee_name || "Unassigned"}
      </p>
      <div className="mt-2">
        <Badge tone={priorityTone(task.priority)}>{task.priority}</Badge>
      </div>
      <select
        className="mt-2 w-full rounded-lg border border-line bg-bg px-2 py-1 text-xs"
        value={task.status}
        onPointerDown={(e) => e.stopPropagation()}
        onChange={(e) => onStatus(task.id, e.target.value)}
      >
        {COLUMNS.map((s) => (
          <option key={s} value={s}>
            {prettyStatus(s)}
          </option>
        ))}
      </select>
    </div>
  );
}
