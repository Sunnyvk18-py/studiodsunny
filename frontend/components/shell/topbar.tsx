"use client";

import { Avatar, Badge, Button } from "@/components/ui";
import { LiveClock } from "@/components/live-clock";
import { useAuth } from "@/lib/auth";
import { endpoints } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useUI } from "@/stores/ui";
import { useQuery } from "@tanstack/react-query";
import { Bell, Moon, PanelLeft, Plus, Search, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function Topbar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const toggleSidebar = useUI((s) => s.toggleSidebar);
  const setCommandOpen = useUI((s) => s.setCommandOpen);
  const setQuickCreateOpen = useUI((s) => s.setQuickCreateOpen);
  const { setTheme, resolvedTheme } = useTheme();
  const notes = useQuery({ queryKey: ["notifications"], queryFn: endpoints.notifications });
  const unread = notes.data?.filter((n) => !n.read_at).length || 0;

  const crumbs = pathname
    .split("/")
    .filter(Boolean)
    .map((part, i, arr) => ({
      label: part.replace(/-/g, " "),
      href: "/" + arr.slice(0, i + 1).join("/"),
    }));

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-2.5 border-b border-line bg-bg/80 px-3 backdrop-blur-xl md:px-5">
      <button
        onClick={toggleSidebar}
        className="hidden size-9 items-center justify-center rounded-lg text-muted hover:bg-sunken hover:text-ink md:inline-flex"
        aria-label="Toggle sidebar"
      >
        <PanelLeft className="size-4" strokeWidth={1.75} />
      </button>

      <nav className="hidden min-w-0 items-center gap-1 text-[12px] capitalize text-muted sm:flex">
        <Link href="/home" className="hover:text-ink">
          HQ
        </Link>
        {crumbs.map((c) => (
          <span key={c.href} className="flex items-center gap-1">
            <span className="opacity-40">/</span>
            <Link href={c.href} className={cn("truncate hover:text-ink", c.href === pathname && "text-ink")}>
              {c.label}
            </Link>
          </span>
        ))}
      </nav>

      <button
        onClick={() => setCommandOpen(true)}
        className="ml-auto flex h-9 min-w-0 max-w-md flex-1 items-center gap-2 rounded-md border border-line bg-raised px-3 text-left text-[14px] text-muted hover:border-[var(--hairline-strong)] md:max-w-sm"
      >
        <Search className="size-3.5 shrink-0 text-accent" strokeWidth={1.75} />
        <span className="truncate">Search HQ…</span>
        <kbd className="ml-auto hidden rounded-md border border-line px-1.5 py-0.5 text-[10px] text-muted sm:inline">
          ⌘K
        </kbd>
      </button>

      <Badge tone="info" className="hidden lg:inline-flex">
        Hyderabad
      </Badge>
      <span className="hidden text-[12px] tabular-nums text-muted xl:inline">
        <LiveClock />
      </span>

      <Button className="h-9" onClick={() => setQuickCreateOpen(true)}>
        <Plus className="size-3.5" />
        <span className="hidden sm:inline">New</span>
      </Button>

      <Link href="/notifications" className="relative grid size-9 place-items-center rounded-lg text-muted hover:bg-sunken hover:text-ink">
        <Bell className="size-4" strokeWidth={1.75} />
        {unread ? (
          <span className="absolute right-1.5 top-1.5 grid size-4 place-items-center rounded-full bg-accent text-[9px] font-semibold text-accent-fg">
            {unread > 9 ? "9+" : unread}
          </span>
        ) : null}
      </Link>

      <button
        onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
        className="grid size-9 place-items-center rounded-lg text-muted hover:bg-sunken hover:text-ink"
        aria-label="Toggle theme"
      >
        {resolvedTheme === "dark" ? <Sun className="size-4" strokeWidth={1.75} /> : <Moon className="size-4" strokeWidth={1.75} />}
      </button>

      <div className="hidden md:block">
        <Avatar name={user?.display_name || "SS"} size={28} />
      </div>
    </header>
  );
}
