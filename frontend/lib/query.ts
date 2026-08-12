import { mutationOptions, queryOptions } from "@tanstack/react-query";
import { endpoints } from "./api";
import type { paths } from "./api-schema";

type ChatChannels = paths["/api/v1/chat/channels"]["get"]["responses"]["200"]["content"]["application/json"];
type ChatMessages = paths["/api/v1/chat/channels/{slug}/messages"]["get"]["responses"]["200"]["content"]["application/json"];
type TaskList = paths["/api/v1/tasks"]["get"]["responses"]["200"]["content"]["application/json"];

export const chatChannelsQuery = queryOptions({
  queryKey: ["chat-channels"],
  queryFn: () => endpoints.chatChannels() as Promise<ChatChannels>,
});

export const chatMessagesQuery = (slug: string) =>
  queryOptions({
    queryKey: ["chat-messages", slug],
    queryFn: () => endpoints.chatMessages(slug) as Promise<ChatMessages>,
  });

export const sendChatMutation = (slug: string) =>
  mutationOptions({
    mutationFn: (body: string) => endpoints.sendChatMessage(slug, body),
  });

export const tasksQuery = (mine = false) =>
  queryOptions({
    queryKey: ["tasks", mine],
    queryFn: () => endpoints.tasks(mine ? { mine: "true" } : undefined) as Promise<TaskList>,
  });

export const updateTaskMutation = mutationOptions({
  mutationFn: ({ id, status }: { id: string; status: string }) => endpoints.updateTask(id, { status }),
});

export const deskQuery = queryOptions({
  queryKey: ["desk"],
  queryFn: endpoints.desk,
});

export const auditQuery = queryOptions({
  queryKey: ["audit"],
  queryFn: () => endpoints.audit(),
});

export const docsQuery = (params?: Record<string, string>) =>
  queryOptions({
    queryKey: ["docs", params || {}],
    queryFn: () => endpoints.docs(params),
  });

export const docQuery = (id: string) =>
  queryOptions({
    queryKey: ["doc", id],
    queryFn: () => endpoints.doc(id),
  });
