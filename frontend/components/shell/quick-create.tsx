"use client";

import { useAuth } from "@/lib/auth";
import { useUI } from "@/stores/ui";
import { Building2, FolderKanban, Receipt, UserPlus, CheckSquare } from "lucide-react";
import Link from "next/link";

const items = [
  { href: "/projects/new", label: "New Project", icon: FolderKanban },
  { href: "/clients/new", label: "Add Client", icon: Building2, perm: "clients:write" },
  { href: "/team?new=1", label: "Add Employee", icon: UserPlus, perm: "employees:write" },
  { href: "/tasks?new=1", label: "Create Task", icon: CheckSquare },
  { href: "/finance", label: "Create Invoice", icon: Receipt, perm: "finance:write" },
];

export function QuickCreate() {
  const open = useUI((s) => s.quickCreateOpen);
  const setOpen = useUI((s) => s.setQuickCreateOpen);
  const { can } = useAuth();
  if (!open) return null;

  const visible = items.filter((item) => !item.perm || can(item.perm));

  return (
    <div className="fixed inset-0 z-50 bg-[#12121a]/70 p-3 backdrop-blur-sm" onClick={() => setOpen(false)}>
      <div className="panel-e2 panel mx-auto mt-[18vh] max-w-md p-4" onClick={(e) => e.stopPropagation()}>
        <p className="kicker mb-3 px-1">Create</p>
        <div className="grid gap-1.5 sm:grid-cols-2">
          {visible.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className="flex h-11 items-center gap-2.5 rounded-xl px-3 text-[13px] font-medium hover:bg-sunken"
              >
                <Icon className="size-4 text-accent" strokeWidth={1.75} />
                {item.label}
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
