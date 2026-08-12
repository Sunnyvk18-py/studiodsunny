"use client";

import { Avatar, PageHeader, Skeleton } from "@/components/ui";
import { ChatMessage, endpoints } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { chatChannelsQuery, chatMessagesQuery } from "@/lib/query";
import { sendHeartbeat, sendTyping, subscribeRealtime } from "@/lib/realtime";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { useEffect, useMemo, useOptimistic, useRef, useState, useTransition } from "react";

export default function MessagesPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [slug, setSlug] = useState("general");
  const [draft, setDraft] = useState("");
  const [typingName, setTypingName] = useState<string | null>(null);
  const [present, setPresent] = useState<string[]>([]);
  const [, startTransition] = useTransition();
  const parentRef = useRef<HTMLDivElement>(null);

  const channels = useQuery(chatChannelsQuery);
  const messages = useQuery(chatMessagesQuery(slug));
  const [optimisticMessages, addOptimistic] = useOptimistic(
    messages.data || [],
    (state: ChatMessage[], incoming: ChatMessage) =>
      state.some((m) => m.id === incoming.id) ? state : [...state, incoming],
  );

  const send = useMutation({
    mutationFn: (body: string) => endpoints.sendChatMessage(slug, body),
    onSuccess: (msg) => {
      qc.setQueryData<ChatMessage[]>(["chat-messages", slug], (prev) => {
        const next = prev || [];
        if (next.some((m) => m.id === msg.id)) return next;
        return [...next, msg];
      });
    },
  });

  useEffect(() => {
    const unsub = subscribeRealtime(slug, (event) => {
      if (event.type === "message" && event.channel === slug && event.message) {
        qc.setQueryData<ChatMessage[]>(["chat-messages", slug], (prev) => {
          const next = prev || [];
          if (next.some((m) => m.id === event.message!.id)) return next;
          return [...next, event.message!];
        });
      }
      if (event.type === "message_updated" && event.channel === slug && event.message) {
        qc.setQueryData<ChatMessage[]>(["chat-messages", slug], (prev) =>
          (prev || []).map((m) => (m.id === event.message!.id ? { ...m, ...event.message! } : m)),
        );
      }
      if (event.type === "message_deleted" && event.channel === slug && event.message_id) {
        const mid = event.message_id;
        qc.setQueryData<ChatMessage[]>(["chat-messages", slug], (prev) =>
          (prev || []).filter((m) => m.id !== mid),
        );
      }
      if (event.type === "typing" && event.channel === slug && event.user?.id !== user?.id) {
        setTypingName(event.user?.display_name || null);
        window.setTimeout(() => setTypingName(null), 1800);
      }
      if (event.type === "presence" && event.channel === slug) {
        setPresent(event.user_ids || []);
      }
    });
    const beat = window.setInterval(() => sendHeartbeat(slug), 15000);
    sendHeartbeat(slug);
    return () => {
      unsub();
      window.clearInterval(beat);
    };
  }, [slug, qc, user?.id]);

  const virtualizer = useVirtualizer({
    count: optimisticMessages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 72,
    overscan: 12,
  });

  useEffect(() => {
    if (!optimisticMessages.length) return;
    virtualizer.scrollToIndex(optimisticMessages.length - 1, { align: "end" });
  }, [optimisticMessages.length, virtualizer]);

  const active = useMemo(
    () => (channels.data || []).find((c) => c.slug === slug),
    [channels.data, slug],
  );

  return (
    <div className="mx-auto flex h-[calc(100dvh-7.5rem)] max-w-[1200px] flex-col">
      <PageHeader kicker="Conversation" title="Messages" description="Presence-aware channels. One socket, multiplexed." />
      <div className="grid min-h-0 flex-1 gap-3 md:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="panel scroll-thin overflow-y-auto p-2">
          {(channels.data || []).map((c) => (
            <button
              key={c.id}
              onClick={() => setSlug(c.slug)}
              className={`mb-0.5 flex w-full flex-col rounded-md px-3 py-2 text-left ${
                slug === c.slug ? "bg-sunken text-ink" : "text-muted hover:bg-sunken/60 hover:text-ink"
              }`}
            >
              <span className="text-[14px] font-medium">#{c.slug}</span>
              <span className="text-[12px] text-muted">{c.topic}</span>
            </button>
          ))}
        </aside>

        <section className="panel flex min-h-0 flex-col">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <div>
              <p className="text-[14px] font-semibold">#{active?.slug || slug}</p>
              <p className="text-[12px] text-muted">{active?.topic || "Channel"}</p>
            </div>
            <p className="text-[12px] text-muted">{present.length || 1} here</p>
          </div>

          <div ref={parentRef} className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-4">
            {messages.isLoading ? (
              <Skeleton className="h-40" />
            ) : (
              <div style={{ height: virtualizer.getTotalSize(), position: "relative", width: "100%" }}>
                {virtualizer.getVirtualItems().map((row) => {
                  const m = optimisticMessages[row.index];
                  return (
                    <div
                      key={m.id}
                      data-index={row.index}
                      ref={virtualizer.measureElement}
                      className="absolute left-0 top-0 w-full pb-4"
                      style={{ transform: `translateY(${row.start}px)` }}
                    >
                      <div className="flex gap-3">
                        <Avatar name={m.author?.display_name || "HQ"} size={32} />
                        <div>
                          <p className="text-[13px] text-muted">
                            <span className="font-medium text-ink">{m.author?.display_name || "Unknown"}</span>
                            <span className="ml-2">{format(new Date(m.created_at), "HH:mm")}</span>
                          </p>
                          <p className="mt-0.5 whitespace-pre-wrap text-[14px] leading-6">{m.body}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <form
            className="border-t border-line p-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (!draft.trim() || !user) return;
              const body = draft.trim();
              const temp: ChatMessage = {
                id: `optimistic-${Date.now()}`,
                channel_id: active?.id || "",
                author_id: user.id,
                body,
                created_at: new Date().toISOString(),
                author: {
                  id: user.id,
                  display_name: user.display_name,
                  email: user.email,
                  role_key: user.role_key,
                  avatar_url: user.avatar_url,
                },
              };
              setDraft("");
              startTransition(() => {
                addOptimistic(temp);
                send.mutate(body);
              });
            }}
          >
            {typingName ? <p className="mb-1 text-[12px] text-muted">{typingName} is typing…</p> : null}
            <input
              value={draft}
              onChange={(e) => {
                setDraft(e.target.value);
                sendTyping(slug);
              }}
              placeholder={`Message #${slug}`}
              className="h-11 w-full rounded-md border border-line bg-bg px-3 text-[14px] outline-none focus:border-accent"
            />
          </form>
        </section>
      </div>
    </div>
  );
}
