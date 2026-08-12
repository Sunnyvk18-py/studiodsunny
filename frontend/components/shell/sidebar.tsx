"use client";

import { Mark } from "@/components/mark";
import { Avatar } from "@/components/ui";
import { LiveClock } from "@/components/live-clock";
import { useAuth } from "@/lib/auth";
import { ROLE_LABELS } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useUI } from "@/stores/ui";
import { HelpCircle, LogOut, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { adminNav, primaryNav } from "./nav";

export function Sidebar() {
  const pathname = usePathname();
  const { user, signOut, can } = useAuth();
  const collapsed = useUI((s) => s.sidebarCollapsed);
  const showAdmin = can("settings:write") || user?.role_key === "founder" || user?.is_superadmin;

  return (
    <aside
      className={cn(
        "sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-line bg-raised md:flex",
        collapsed ? "w-[68px]" : "w-[240px]",
      )}
    >
      <div
        className={cn(
          "relative overflow-hidden border-b border-line px-3 py-4",
          collapsed && "px-2",
        )}
      >
        <div className={cn("relative flex items-center gap-2.5", collapsed && "justify-center")}>
          <Mark className="size-8 shrink-0" />
          {!collapsed ? (
            <div className="min-w-0 leading-tight">
              <p className="truncate text-[14px] font-semibold tracking-tight text-ink">Studio Sunny</p>
              <p className="text-[12px] text-muted">HQ · Company OS</p>
            </div>
          ) : null}
        </div>
        {!collapsed ? (
          <div className="relative mt-3 flex items-center justify-between rounded-lg border border-line bg-sunken/70 px-2.5 py-1.5">
            <span className="flex items-center gap-1.5 text-[12px] font-medium text-ok">
              <span className="size-1.5 rounded-full bg-ok" />
              Live
            </span>
            <LiveClock className="text-[12px] tabular-nums text-muted" />
          </div>
        ) : null}
      </div>

      <nav className="scroll-thin flex-1 overflow-y-auto px-2 py-3">
        <p className={cn("px-2 pb-1.5 text-[11px] font-semibold tracking-[0.12em] uppercase text-muted", collapsed && "sr-only")}>
          Workspace
        </p>
        {primaryNav
          .filter((item) => !item.perm || can(item.perm))
          .map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.label}
              className={cn(
                "relative mb-0.5 flex h-9 items-center gap-2.5 rounded-md px-2.5 text-[14px] transition",
                active
                  ? "bg-[color-mix(in_oklch,var(--accent)_14%,transparent)] font-medium text-ink"
                  : "text-muted hover:bg-sunken hover:text-ink",
                collapsed && "justify-center px-0",
              )}
            >
              {active ? <span className="absolute left-0 top-2 bottom-2 w-[2px] rounded-full bg-accent" /> : null}
              <Icon className={cn("size-4 shrink-0", active && "text-accent")} strokeWidth={1.75} />
              {!collapsed ? <span className="truncate">{item.label}</span> : null}
            </Link>
          );
        })}

        {showAdmin ? (
          <>
            <p className={cn("mt-5 px-2 pb-1.5 text-[11px] font-semibold tracking-[0.12em] uppercase text-muted", collapsed && "sr-only")}>
              Admin
            </p>
            {adminNav
              .filter((item) => !item.perm || can(item.perm) || user?.role_key === "founder")
              .map((item) => {
              const active = pathname === item.href || pathname.startsWith(item.href + "/");
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  title={item.label}
                  className={cn(
                    "relative mb-0.5 flex h-9 items-center gap-2.5 rounded-md px-2.5 text-[14px] transition",
                    active
                      ? "bg-[color-mix(in_oklch,var(--accent)_14%,transparent)] font-medium text-ink"
                      : "text-muted hover:bg-sunken hover:text-ink",
                    collapsed && "justify-center px-0",
                  )}
                >
                  {active ? <span className="absolute left-0 top-2 bottom-2 w-[2px] rounded-full bg-accent" /> : null}
                  <Icon className={cn("size-4 shrink-0", active && "text-accent")} strokeWidth={1.75} />
                  {!collapsed ? <span className="truncate">{item.label}</span> : null}
                </Link>
              );
            })}
          </>
        ) : null}
      </nav>

      <div className="border-t border-line p-2.5">
        <div className={cn("mb-1 flex items-center gap-2.5 rounded-lg px-1.5 py-1.5", collapsed && "justify-center")}>
          <span className="relative">
            <Avatar name={user?.display_name || "SS"} size={28} />
            <span className="absolute -bottom-0.5 -right-0.5 size-2 rounded-full border-2 border-raised bg-ok" />
          </span>
          {!collapsed && user ? (
            <div className="min-w-0">
              <p className="truncate text-[14px] font-medium text-ink">{user.display_name}</p>
              <p className="truncate text-[12px] text-muted">{ROLE_LABELS[user.role_key] || user.role_key}</p>
            </div>
          ) : null}
        </div>
        <div className={cn("flex", collapsed ? "flex-col items-center" : "px-1")}>
          <Link href="/settings" className="rounded-lg p-1.5 text-muted hover:bg-sunken hover:text-ink" title="Settings">
            <Settings className="size-3.5" />
          </Link>
          <Link href="/help" className="rounded-lg p-1.5 text-muted hover:bg-sunken hover:text-ink" title="Help">
            <HelpCircle className="size-3.5" />
          </Link>
          <button onClick={() => signOut()} className="rounded-lg p-1.5 text-muted hover:bg-sunken hover:text-ink" title="Sign out">
            <LogOut className="size-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
