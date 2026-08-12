"use client";

import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { CommandPalette } from "./command-palette";
import { QuickCreate } from "./quick-create";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { Skeleton } from "../ui";

export function HQShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="grid min-h-dvh place-items-center bg-bg">
        <div className="w-72 space-y-3">
          <Skeleton className="h-6 w-36" />
          <Skeleton className="h-24 w-full" />
          <p className="text-center text-[12px] text-muted">Opening headquarters…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh bg-bg">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="scroll-thin flex-1 overflow-y-auto bg-bg px-4 py-6 md:px-7 md:py-7">
          <div className="hq-enter">{children}</div>
        </main>
      </div>
      <CommandPalette />
      <QuickCreate />
    </div>
  );
}
