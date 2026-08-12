"use client";

import { DocEditor } from "@/components/docs/doc-editor";
import { Badge, Button, Input, PageHeader, Select, Skeleton } from "@/components/ui";
import { Doc, endpoints } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { prettyStatus } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

export default function DocDetailPage() {
  const { user } = useAuth();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const qc = useQueryClient();
  const doc = useQuery({ queryKey: ["doc", id], queryFn: () => endpoints.doc(id) });
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState("draft");
  const [kind, setKind] = useState("page");
  const [summary, setSummary] = useState("");
  const [content, setContent] = useState<Record<string, unknown> | null>(null);
  const [yjsB64, setYjsB64] = useState<string | undefined>();
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!doc.data) return;
    setTitle(doc.data.title);
    setStatus(doc.data.status);
    setKind(doc.data.kind);
    setSummary(doc.data.summary || "");
    setContent(doc.data.content);
    setDirty(false);
  }, [doc.data]);

  const save = useMutation({
    mutationFn: () =>
      endpoints.updateDoc(id, {
        title,
        status,
        kind,
        summary: summary || null,
        content: content || undefined,
        yjs_state_b64: yjsB64,
      }),
    onSuccess: (updated) => {
      qc.setQueryData(["doc", id], updated);
      qc.invalidateQueries({ queryKey: ["docs"] });
      setDirty(false);
      toast.success("Saved");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: () => endpoints.deleteDoc(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["docs"] });
      toast.success("Doc archived");
      router.push("/docs");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        if (dirty && !save.isPending) save.mutate();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dirty, save]);

  if (doc.isLoading || !doc.data || !content) {
    return <Skeleton className="h-80" />;
  }

  const d = doc.data as Doc;

  return (
    <div className="mx-auto max-w-[900px]">
      <PageHeader
        kicker={d.project_name || d.client_name || "Docs"}
        title={title || "Untitled"}
        description={
          d.updated_at
            ? `Last edited ${format(new Date(d.updated_at), "MMM d, yyyy · HH:mm")}${d.author_name ? ` · ${d.author_name}` : ""}`
            : undefined
        }
        actions={
          <>
            <Link href="/docs">
              <Button variant="ghost">All docs</Button>
            </Link>
            <Button variant="outline" onClick={() => remove.mutate()} loading={remove.isPending}>
              Archive
            </Button>
            <Button onClick={() => save.mutate()} loading={save.isPending} disabled={!dirty && !save.isPending}>
              {dirty ? "Save" : "Saved"}
            </Button>
          </>
        }
      />

      <div className="mb-5 grid gap-3 sm:grid-cols-[1fr_140px_140px]">
        <Input
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
            setDirty(true);
          }}
          placeholder="Title"
          className="text-[16px] font-semibold"
        />
        <Select
          value={kind}
          onChange={(e) => {
            setKind(e.target.value);
            setDirty(true);
          }}
        >
          {["page", "brief", "handbook", "template", "sop"].map((k) => (
            <option key={k} value={k}>
              {prettyStatus(k)}
            </option>
          ))}
        </Select>
        <Select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setDirty(true);
          }}
        >
          {["draft", "published", "archived"].map((s) => (
            <option key={s} value={s}>
              {prettyStatus(s)}
            </option>
          ))}
        </Select>
      </div>

      <Input
        className="mb-5"
        value={summary}
        onChange={(e) => {
          setSummary(e.target.value);
          setDirty(true);
        }}
        placeholder="One-line summary"
      />

      <div className="mb-3 flex gap-2">
        <Badge>{prettyStatus(kind)}</Badge>
        <Badge tone={status === "published" ? "ok" : "neutral"}>{prettyStatus(status)}</Badge>
        {d.project_id ? (
          <Link href={`/projects/${d.project_id}`} className="text-[12px] text-muted hover:text-ink">
            Open project →
          </Link>
        ) : null}
      </div>

      <div className="panel p-5">
        <DocEditor
          docId={id}
          content={content}
          userName={user?.display_name || "Teammate"}
          onChange={(json, state) => {
            setContent(json);
            if (state) setYjsB64(state);
            setDirty(true);
          }}
          placeholder="Write the brief, SOP, or decision…"
        />
      </div>
    </div>
  );
}
