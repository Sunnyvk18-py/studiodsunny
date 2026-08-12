"use client";

import Collaboration from "@tiptap/extension-collaboration";
import CollaborationCaret from "@tiptap/extension-collaboration-caret";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useEffect, useMemo, useRef, useState } from "react";
import * as Y from "yjs";
import { Awareness } from "y-protocols/awareness";
import * as awarenessProtocol from "y-protocols/awareness";
import { Button } from "@/components/ui";

type Props = {
  docId: string;
  content: Record<string, unknown>;
  userName?: string;
  userColor?: string;
  editable?: boolean;
  onChange?: (json: Record<string, unknown>, yjsB64?: string) => void;
  placeholder?: string;
};

function toB64(u8: Uint8Array) {
  let s = "";
  u8.forEach((b) => {
    s += String.fromCharCode(b);
  });
  return btoa(s);
}

function fromB64(b64: string) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export function DocEditor({
  docId,
  content,
  userName = "Teammate",
  userColor = "#e8b86d",
  editable = true,
  onChange,
  placeholder = "Start writing…",
}: Props) {
  const ydoc = useMemo(() => new Y.Doc(), [docId]);
  const awareness = useMemo(() => new Awareness(ydoc), [ydoc]);
  const provider = useMemo(() => ({ awareness }), [awareness]);
  const [peers, setPeers] = useState<string[]>([]);
  const seeded = useRef(false);
  const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    awareness.setLocalStateField("user", { name: userName, color: userColor });
    const syncPeers = () => {
      const names: string[] = [];
      awareness.getStates().forEach((state) => {
        const n = state?.user?.name;
        if (n) names.push(n);
      });
      setPeers(Array.from(new Set(names)));
    };
    awareness.on("change", syncPeers);
    syncPeers();
    return () => {
      awareness.off("change", syncPeers);
      awareness.destroy();
    };
  }, [awareness, userColor, userName]);

  useEffect(() => {
    seeded.current = false;
    let ws: WebSocket | null = null;
    let closed = false;

    const connect = async () => {
      try {
        const res = await fetch(`${api}/api/v1/docs/${docId}/yjs`, { credentials: "include" });
        if (res.ok) {
          const body = await res.json();
          if (body.yjs_state_b64) {
            Y.applyUpdate(ydoc, fromB64(body.yjs_state_b64), "remote");
            seeded.current = true;
          }
        }
      } catch {
        /* offline seed from tip tap JSON below */
      }

      const wsUrl = api.replace(/^http/, "ws") + `/api/v1/docs/${docId}/collab`;
      ws = new WebSocket(wsUrl);
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if ((msg.type === "yjs" || msg.type === "yjs-init") && msg.update && msg.sender_id !== "local") {
            Y.applyUpdate(ydoc, fromB64(msg.update), "remote");
            seeded.current = true;
          }
          if (msg.type === "awareness-bin" && msg.update && msg.sender_id !== String(awareness.clientID)) {
            awarenessProtocol.applyAwarenessUpdate(awareness, fromB64(msg.update), "remote");
          }
          if (msg.type === "awareness" && msg.awareness?.name) {
            setPeers((prev) => Array.from(new Set([...prev.filter((p) => p !== msg.awareness.name), msg.awareness.name])));
          }
          if (msg.type === "presence" && msg.user?.display_name) {
            setPeers((prev) => Array.from(new Set([...prev, msg.user.display_name])));
          }
        } catch {
          /* ignore */
        }
      };

      const onUpdate = (update: Uint8Array, origin: unknown) => {
        if (origin === "remote" || !ws || ws.readyState !== WebSocket.OPEN) return;
        ws.send(JSON.stringify({ type: "yjs", update: toB64(update) }));
      };
      ydoc.on("update", onUpdate);

      const onAwareness = (
        { added, updated, removed }: { added: number[]; updated: number[]; removed: number[] },
        origin: unknown,
      ) => {
        if (origin === "remote" || !ws || ws.readyState !== WebSocket.OPEN) return;
        const changed = added.concat(updated, removed);
        const update = awarenessProtocol.encodeAwarenessUpdate(awareness, changed);
        ws.send(
          JSON.stringify({
            type: "awareness-bin",
            update: toB64(update),
            sender_id: String(awareness.clientID),
            awareness: { name: userName, color: userColor },
          }),
        );
      };
      awareness.on("update", onAwareness);

      const beat = window.setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "awareness", awareness: { name: userName, color: userColor } }));
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 12000);

      // push local awareness once connected
      const ready = window.setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          const update = awarenessProtocol.encodeAwarenessUpdate(awareness, [awareness.clientID]);
          ws.send(
            JSON.stringify({
              type: "awareness-bin",
              update: toB64(update),
              sender_id: String(awareness.clientID),
              awareness: { name: userName, color: userColor },
            }),
          );
          window.clearInterval(ready);
        }
      }, 400);

      return () => {
        ydoc.off("update", onUpdate);
        awareness.off("update", onAwareness);
        window.clearInterval(beat);
        window.clearInterval(ready);
      };
    };

    let cleanupInner: (() => void) | undefined;
    connect().then((c) => {
      if (!closed) cleanupInner = c;
    });

    return () => {
      closed = true;
      cleanupInner?.();
      ws?.close();
      ydoc.destroy();
    };
  }, [api, awareness, docId, userColor, userName, ydoc]);

  const editor = useEditor(
    {
      extensions: [
        StarterKit.configure({
          heading: { levels: [2, 3] },
          undoRedo: false,
        }),
        Placeholder.configure({ placeholder }),
        Link.configure({
          openOnClick: false,
          HTMLAttributes: { class: "doc-link" },
        }),
        Collaboration.configure({ document: ydoc }),
        CollaborationCaret.configure({
          provider,
          user: { name: userName, color: userColor },
        }),
      ],
      editable,
      immediatelyRender: false,
      editorProps: {
        attributes: {
          class: "doc-prose outline-none min-h-[320px] px-1 py-2",
        },
      },
      onUpdate: ({ editor: ed }) => {
        const json = ed.getJSON() as Record<string, unknown>;
        onChange?.(json, toB64(Y.encodeStateAsUpdate(ydoc)));
      },
    },
    [ydoc, provider, userName, userColor],
  );

  useEffect(() => {
    if (!editor) return;
    editor.setEditable(editable);
  }, [editor, editable]);

  useEffect(() => {
    if (!editor || seeded.current) return;
    if (content && Object.keys(content).length) {
      editor.commands.setContent(content, { emitUpdate: false });
      seeded.current = true;
    }
  }, [editor, content]);

  if (!editor) return <div className="min-h-[320px] animate-pulse rounded-md bg-sunken" />;

  return (
    <div className="space-y-2">
      {peers.length ? (
        <p className="text-[12px] text-muted">Live · {peers.filter((p) => p !== userName).join(", ") || "just you"}</p>
      ) : (
        <p className="text-[12px] text-muted">Live collab on · Yjs + carets</p>
      )}
      {editable ? (
        <div className="flex flex-wrap gap-1 border-b border-line pb-2">
          <ToolbarBtn active={editor.isActive("bold")} onClick={() => editor.chain().focus().toggleBold().run()} label="Bold" />
          <ToolbarBtn active={editor.isActive("italic")} onClick={() => editor.chain().focus().toggleItalic().run()} label="Italic" />
          <ToolbarBtn
            active={editor.isActive("heading", { level: 2 })}
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            label="H2"
          />
          <ToolbarBtn
            active={editor.isActive("heading", { level: 3 })}
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            label="H3"
          />
          <ToolbarBtn
            active={editor.isActive("bulletList")}
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            label="List"
          />
          <ToolbarBtn
            active={editor.isActive("orderedList")}
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            label="1."
          />
          <ToolbarBtn
            active={editor.isActive("blockquote")}
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            label="Quote"
          />
        </div>
      ) : null}
      <EditorContent editor={editor} />
    </div>
  );
}

function ToolbarBtn({
  label,
  onClick,
  active,
}: {
  label: string;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <Button
      type="button"
      variant={active ? "subtle" : "ghost"}
      className={`h-8 px-2 text-[12px] ${active ? "text-ink" : "text-muted"}`}
      onClick={onClick}
    >
      {label}
    </Button>
  );
}
