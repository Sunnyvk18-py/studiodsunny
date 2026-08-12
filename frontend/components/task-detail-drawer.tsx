"use client";

import { Avatar, Button, Input, Select, Skeleton, Textarea } from "@/components/ui";
import { TaskComment, endpoints } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { prettyStatus } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { toast } from "sonner";

const STATUSES = ["backlog", "todo", "in_progress", "review", "blocked", "completed"] as const;
const PRIORITIES = ["low", "medium", "high", "urgent"] as const;

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function TaskDetailDrawer({
  taskId,
  onClose,
  returnFocusTo,
}: {
  taskId: string;
  onClose: () => void;
  returnFocusTo?: HTMLElement | null;
}) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const skipBlurSave = useRef(false);
  const qc = useQueryClient();
  const { user } = useAuth();
  const isFounder = user?.role_key === "founder" || user?.is_superadmin;

  const task = useQuery({
    queryKey: ["task", taskId],
    queryFn: () => endpoints.task(taskId),
  });
  const comments = useQuery({
    queryKey: ["task-comments", taskId],
    queryFn: () => endpoints.taskComments(taskId),
  });
  const people = useQuery({ queryKey: ["employees"], queryFn: () => endpoints.employees() });

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [commentBody, setCommentBody] = useState("");
  const [editingCommentId, setEditingCommentId] = useState<string | null>(null);
  const [editingCommentBody, setEditingCommentBody] = useState("");

  useEffect(() => {
    if (!task.data) return;
    setTitle(task.data.title);
    setDescription(task.data.description || "");
  }, [task.data]);

  function discardDraftsAndClose() {
    skipBlurSave.current = true;
    if (task.data) {
      setTitle(task.data.title);
      setDescription(task.data.description || "");
    }
    onClose();
  }

  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    const previouslyFocused = returnFocusTo || (document.activeElement as HTMLElement | null);
    const nodes = () =>
      Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((el) => !el.hasAttribute("disabled"));
    nodes()[0]?.focus();

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        discardDraftsAndClose();
        return;
      }
      if (e.key !== "Tab") return;
      const list = nodes();
      if (!list.length) {
        e.preventDefault();
        return;
      }
      const firstEl = list[0];
      const lastEl = list[list.length - 1];
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocused?.focus?.();
      skipBlurSave.current = false;
    };
    // discardDraftsAndClose closes over latest task.data / onClose
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId, onClose, returnFocusTo, task.data]);

  const patchTask = useMutation({
    mutationFn: (data: Record<string, unknown>) => endpoints.updateTask(taskId, data),
    onSuccess: () => {
      // Invalidate instead of writing the response — rapid field changes can race.
      void qc.invalidateQueries({ queryKey: ["task", taskId] });
      void qc.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const postComment = useMutation({
    mutationFn: (body: string) => endpoints.addTaskComment(taskId, body),
    onMutate: async (body) => {
      await qc.cancelQueries({ queryKey: ["task-comments", taskId] });
      const previous = qc.getQueryData<TaskComment[]>(["task-comments", taskId]);
      const optimistic: TaskComment = {
        id: `temp-${Date.now()}`,
        task_id: taskId,
        author_id: user?.id || "",
        body,
        created_at: new Date().toISOString(),
        author: user
          ? {
              id: user.id,
              display_name: user.display_name,
              email: user.email,
              role_key: user.role_key,
              avatar_url: user.avatar_url,
            }
          : null,
      };
      qc.setQueryData<TaskComment[]>(["task-comments", taskId], (old) => [...(old || []), optimistic]);
      setCommentBody("");
      return { previous, tempId: optimistic.id, body };
    },
    onError: (e: Error, _body, ctx) => {
      if (ctx?.previous) qc.setQueryData(["task-comments", taskId], ctx.previous);
      if (ctx?.body) setCommentBody(ctx.body);
      toast.error(e.message);
    },
    onSuccess: (created, _body, ctx) => {
      qc.setQueryData<TaskComment[]>(["task-comments", taskId], (old) =>
        (old || []).map((c) => (c.id === ctx?.tempId ? created : c)),
      );
    },
    onSettled: (_data, error) => {
      // Skip refetch on failure so the rollback sticks while offline.
      if (!error) void qc.invalidateQueries({ queryKey: ["task-comments", taskId] });
    },
  });

  const updateComment = useMutation({
    mutationFn: ({ commentId, body }: { commentId: string; body: string }) =>
      endpoints.updateTaskComment(taskId, commentId, body),
    onSuccess: (updated) => {
      qc.setQueryData<TaskComment[]>(["task-comments", taskId], (old) =>
        (old || []).map((c) => (c.id === updated.id ? updated : c)),
      );
      setEditingCommentId(null);
      toast.success("Comment updated");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteComment = useMutation({
    mutationFn: (commentId: string) => endpoints.deleteTaskComment(taskId, commentId),
    onMutate: async (commentId) => {
      await qc.cancelQueries({ queryKey: ["task-comments", taskId] });
      const previous = qc.getQueryData<TaskComment[]>(["task-comments", taskId]);
      qc.setQueryData<TaskComment[]>(["task-comments", taskId], (old) =>
        (old || []).filter((c) => c.id !== commentId),
      );
      return { previous };
    },
    onError: (e: Error, _id, ctx) => {
      if (ctx?.previous) qc.setQueryData(["task-comments", taskId], ctx.previous);
      toast.error(e.message);
    },
    onSettled: (_data, error) => {
      if (!error) void qc.invalidateQueries({ queryKey: ["task-comments", taskId] });
    },
  });

  function saveField(data: Record<string, unknown>) {
    patchTask.mutate(data);
  }

  function submitComment() {
    const body = commentBody.trim();
    if (!body || postComment.isPending) return;
    postComment.mutate(body);
  }

  const t = task.data;

  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="presentation">
      <button
        type="button"
        className="absolute inset-0 bg-black/35"
        aria-label="Close task detail"
        onClick={discardDraftsAndClose}
      />
      <aside
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative flex h-full w-full max-w-lg flex-col border-l border-line bg-raised shadow-xl"
      >
        <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
          <div className="min-w-0 flex-1">
            <p className="kicker mb-1">{t?.project_name || "Task"}</p>
            {task.isLoading || !t ? (
              <Skeleton className="h-8 w-3/4" />
            ) : (
              <Input
                id={titleId}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                onBlur={() => {
                  if (skipBlurSave.current) return;
                  if (title.trim() && title !== t.title) saveField({ title: title.trim() });
                }}
                className="h-auto border-transparent bg-transparent px-0 text-[18px] font-semibold focus:border-line"
              />
            )}
          </div>
          <Button type="button" variant="ghost" className="shrink-0 px-2" onClick={discardDraftsAndClose} aria-label="Close">
            <X className="size-4" />
          </Button>
        </div>

        <div className="scroll-thin flex-1 space-y-5 overflow-y-auto px-5 py-4">
          {task.isLoading || !t ? (
            <Skeleton className="h-40" />
          ) : (
            <>
              <label className="block">
                <span className="mb-1.5 block text-[12px] font-medium text-muted">Description</span>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  onBlur={() => {
                    if (skipBlurSave.current) return;
                    const next = description.trim() || null;
                    if ((t.description || null) !== next) saveField({ description: next });
                  }}
                  placeholder="Add a description"
                  className="min-h-24"
                />
              </label>

              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Assignee</span>
                  <Select
                    value={t.assignee_id || ""}
                    onChange={(e) => saveField({ assignee_id: e.target.value || null })}
                  >
                    <option value="">Unassigned</option>
                    {(people.data || []).map((p) => (
                      <option key={p.user_id} value={p.user_id}>
                        {p.display_name}
                      </option>
                    ))}
                  </Select>
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Due date</span>
                  <Input
                    type="date"
                    value={t.due_date || ""}
                    onChange={(e) => saveField({ due_date: e.target.value || null })}
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Priority</span>
                  <Select value={t.priority} onChange={(e) => saveField({ priority: e.target.value })}>
                    {PRIORITIES.map((p) => (
                      <option key={p} value={p}>
                        {prettyStatus(p)}
                      </option>
                    ))}
                  </Select>
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-[12px] font-medium text-muted">Status</span>
                  <Select value={t.status} onChange={(e) => saveField({ status: e.target.value })}>
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {prettyStatus(s)}
                      </option>
                    ))}
                  </Select>
                </label>
              </div>
            </>
          )}

          <section>
            <h3 className="section-title mb-3">Comments</h3>
            {comments.isLoading ? (
              <Skeleton className="h-24" />
            ) : (
              <ul className="space-y-3">
                {(comments.data || []).map((c) => {
                  const own = user?.id === c.author_id;
                  const canMutate = own || isFounder;
                  const editing = editingCommentId === c.id;
                  return (
                    <li key={c.id} className="rounded-lg border border-line bg-bg p-3">
                      <div className="mb-2 flex items-center gap-2">
                        <Avatar name={c.author?.display_name || "?"} size={24} />
                        <div className="min-w-0 flex-1">
                          <p className="text-[13px] font-medium">{c.author?.display_name || "Someone"}</p>
                          <p className="text-[11px] text-muted">{format(new Date(c.created_at), "MMM d · HH:mm")}</p>
                        </div>
                        {canMutate && !editing ? (
                          <div className="flex gap-1">
                            {own ? (
                              <button
                                type="button"
                                className="text-[11px] font-medium text-muted hover:text-ink"
                                onClick={() => {
                                  setEditingCommentId(c.id);
                                  setEditingCommentBody(c.body);
                                }}
                              >
                                Edit
                              </button>
                            ) : null}
                            <button
                              type="button"
                              className="text-[11px] font-medium text-danger hover:underline"
                              onClick={() => deleteComment.mutate(c.id)}
                            >
                              Delete
                            </button>
                          </div>
                        ) : null}
                      </div>
                      {editing ? (
                        <div className="space-y-2">
                          <Textarea
                            value={editingCommentBody}
                            onChange={(e) => setEditingCommentBody(e.target.value)}
                            className="min-h-20"
                          />
                          <div className="flex justify-end gap-2">
                            <Button type="button" variant="ghost" onClick={() => setEditingCommentId(null)}>
                              Cancel
                            </Button>
                            <Button
                              type="button"
                              loading={updateComment.isPending}
                              onClick={() => {
                                const body = editingCommentBody.trim();
                                if (!body) return;
                                updateComment.mutate({ commentId: c.id, body });
                              }}
                            >
                              Save
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <p className="whitespace-pre-wrap text-[14px] leading-6 text-ink">{c.body}</p>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}

            <div className="mt-4">
              <Textarea
                value={commentBody}
                onChange={(e) => setCommentBody(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submitComment();
                  }
                }}
                placeholder="Write a comment… Enter to post, Shift+Enter for newline"
                className="min-h-20"
              />
              <div className="mt-2 flex justify-end">
                <Button type="button" loading={postComment.isPending} onClick={submitComment} disabled={!commentBody.trim()}>
                  Post
                </Button>
              </div>
            </div>
          </section>
        </div>
      </aside>
    </div>
  );
}
