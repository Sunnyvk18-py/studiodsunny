"use client";

import { endpoints, SearchHit } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useUI } from "@/stores/ui";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { primaryNav } from "./nav";

export function CommandPalette() {
  const open = useUI((s) => s.commandOpen);
  const setOpen = useUI((s) => s.setCommandOpen);
  const setQuick = useUI((s) => s.setQuickCreateOpen);
  const { can } = useAuth();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const nav = useMemo(() => primaryNav.filter((n) => !n.perm || can(n.perm)), [can]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  useEffect(() => {
    if (!q.trim()) {
      setHits([]);
      return;
    }
    const t = setTimeout(() => {
      endpoints.search(q).then((r) => setHits(r.results)).catch(() => setHits([]));
    }, 120);
    return () => clearTimeout(t);
  }, [q]);

  const actions = useMemo(
    () => [
      { label: "Create task", href: "/tasks?new=1" },
      { label: "New doc", href: "/docs" },
      { label: "Upload file", href: "/files" },
      { label: "Add client", href: "/clients/new" },
      { label: "New project", href: "/projects/new" },
      { label: "Add employee", href: "/team?new=1" },
      { label: "Ask Sunny AI", href: "/ai" },
      { label: "Open My Desk", href: "/desk" },
    ],
    [],
  );

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-[#12121a]/70 p-3 backdrop-blur-sm" onClick={() => setOpen(false)}>
      <Command
        className="panel-e2 panel mx-auto mt-[14vh] max-w-lg overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <Command.Input
          autoFocus
          value={q}
          onValueChange={setQ}
          placeholder="Search or jump to…"
          className="h-11 w-full border-b border-line bg-transparent px-3.5 text-[13px] outline-none"
        />
        <Command.List className="scroll-thin max-h-[46vh] overflow-y-auto p-1.5">
          <Command.Empty className="px-3 py-5 text-[13px] text-muted">No matches.</Command.Empty>
          {hits.length ? (
            <Command.Group heading="Results" className="px-2 py-1 text-[11px] font-medium text-muted">
              {hits.map((hit) => (
                <Command.Item
                  key={`${hit.type}-${hit.id}`}
                  onSelect={() => {
                    setOpen(false);
                    router.push(hit.href);
                  }}
                  className="flex cursor-pointer items-center justify-between rounded-md px-2.5 py-1.5 text-[13px] aria-selected:bg-sunken"
                >
                  <span>{hit.title}</span>
                  <span className="text-[11px] text-muted">{hit.type}</span>
                </Command.Item>
              ))}
            </Command.Group>
          ) : null}
          <Command.Group heading="Actions" className="px-2 py-1 text-[11px] font-medium text-muted">
            {actions.map((a) => (
              <Command.Item
                key={a.label}
                onSelect={() => {
                  setOpen(false);
                  if (a.label.startsWith("Create") || a.label.startsWith("Add") || a.label.startsWith("New")) {
                    setQuick(false);
                  }
                  router.push(a.href);
                }}
                className="cursor-pointer rounded-md px-2.5 py-1.5 text-[13px] aria-selected:bg-sunken"
              >
                {a.label}
              </Command.Item>
            ))}
          </Command.Group>
          <Command.Group heading="Go to" className="px-2 py-1 text-[11px] font-medium text-muted">
            {nav.map((n) => (
              <Command.Item
                key={n.href}
                onSelect={() => {
                  setOpen(false);
                  router.push(n.href);
                }}
                className="cursor-pointer rounded-md px-2.5 py-1.5 text-[13px] aria-selected:bg-sunken"
              >
                {n.label}
              </Command.Item>
            ))}
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}
