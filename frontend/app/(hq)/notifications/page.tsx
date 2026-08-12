"use client";

import { Badge, Button, PageHeader, Skeleton } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import Link from "next/link";
import { toast } from "sonner";

export default function NotificationsPage() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["notifications"], queryFn: endpoints.notifications });
  const readOne = useMutation({
    mutationFn: (id: string) => endpoints.markNotificationRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
  const readAll = useMutation({
    mutationFn: endpoints.markAllNotificationsRead,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      toast.success("All caught up");
    },
  });

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        kicker="Inbox"
        title="Notifications"
        description="Assignments, payments, mentions, and deadlines."
        actions={
          <Button variant="outline" onClick={() => readAll.mutate()} loading={readAll.isPending}>
            Mark all read
          </Button>
        }
      />
      {q.isLoading ? (
        <Skeleton className="h-64" />
      ) : (
        <div className="space-y-2">
          {(q.data || []).map((n) => (
            <Link
              key={n.id}
              href={n.href || "#"}
              onClick={() => !n.read_at && readOne.mutate(n.id)}
              className={`panel lift relative block overflow-hidden p-4 ${n.read_at ? "opacity-70" : ""}`}
            >
              {!n.read_at ? <span className="absolute inset-y-0 left-0 w-[3px] bg-accent" /> : null}
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold">{n.title}</p>
                  <p className="mt-1 text-[13px] text-muted">{n.body}</p>
                  <p className="mt-2 text-[12px] text-muted">
                    {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
                  </p>
                </div>
                <Badge tone={n.priority === "high" ? "warn" : "neutral"}>{n.priority}</Badge>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
