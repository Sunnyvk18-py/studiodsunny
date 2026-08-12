"use client";

import { PageHeader } from "@/components/ui";

export default function HelpPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader kicker="Support" title="Help" description="Keyboard shortcuts and how HQ is meant to be used." />
      <div className="panel space-y-3 p-5 text-sm">
        <p>
          <kbd className="rounded border border-line px-1.5 py-0.5 text-xs">⌘K</kbd> /{" "}
          <kbd className="rounded border border-line px-1.5 py-0.5 text-xs">Ctrl+K</kbd> opens the command palette.
        </p>
        <p>Start on Home or My Desk. Create a client, then a project, then tasks. Progress and notifications update from the live API.</p>
        <p className="text-muted">Demo password for all seed accounts: SunnyHQ2026!</p>
      </div>
    </div>
  );
}
