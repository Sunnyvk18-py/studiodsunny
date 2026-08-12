"use client";

import { Avatar, Badge, Button, Input, PageHeader, Select, Skeleton } from "@/components/ui";
import { HealthRing } from "@/components/health-ring";
import { ROLE_LABELS, endpoints } from "@/lib/api";
import { prettyStatus } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { toast } from "sonner";

export default function TeamPage() {
  return (
    <Suspense>
      <TeamInner />
    </Suspense>
  );
}

function TeamInner() {
  const { can } = useAuth();
  const params = useSearchParams();
  const showNew = params.get("new") === "1" && can("employees:write");
  const [q, setQ] = useState("");
  const people = useQuery({ queryKey: ["employees", q], queryFn: () => endpoints.employees(q || undefined) });

  return (
    <div className="mx-auto max-w-[1200px]">
      <PageHeader
        kicker="People"
        title="Team"
        description="Directory, capacity, and who can take the next brief."
        actions={can("employees:write") ? <AddEmployeeForm /> : null}
      />

      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search people"
        className="mb-5 h-10 w-full max-w-md rounded-xl border border-line bg-raised px-3 text-[13px] outline-none focus:border-accent/50"
      />

      {showNew ? <p className="mb-4 text-[12px] text-muted">Use the form on the right to add someone to HQ.</p> : null}

      {people.isLoading ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-44" />
          ))}
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(people.data || []).map((e) => (
            <Link key={e.id} href={`/team/${e.id}`} className="panel lift p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="relative">
                    <Avatar name={e.display_name} size={40} />
                    <span className={`absolute -bottom-0.5 -right-0.5 size-2.5 rounded-full border-2 border-raised ${e.availability === "busy" ? "bg-warn" : "bg-ok"}`} />
                  </span>
                  <div>
                    <p className="font-semibold">{e.display_name}</p>
                    <p className="mt-0.5 text-[12px] text-muted">
                      {e.job_title} · {e.department_name || ROLE_LABELS[e.role_key]}
                    </p>
                  </div>
                </div>
                <Badge tone={e.availability === "busy" ? "warn" : "ok"}>{prettyStatus(e.availability)}</Badge>
              </div>
              <p className="mt-4 text-[12px] text-muted">
                {e.location || "—"} · {e.active_projects} active projects
              </p>
              <div className="mt-3">
                <HealthRing
                  value={e.utilization}
                  label="Capacity"
                  tone={e.utilization >= 90 ? "danger" : e.utilization >= 75 ? "warn" : "ok"}
                />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function AddEmployeeForm() {
  const qc = useQueryClient();
  const depts = useQuery({ queryKey: ["departments"], queryFn: endpoints.departments });
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"invite" | "direct">("invite");
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);
  const [form, setForm] = useState({
    email: "",
    password: "SunnyHQ2026!",
    first_name: "",
    last_name: "",
    role_key: "developer",
    job_title: "",
    department_id: "",
    location: "Hyderabad",
  });
  const create = useMutation({
    mutationFn: async () => {
      if (mode === "invite") {
        return endpoints.inviteEmployee({
          email: form.email,
          first_name: form.first_name,
          last_name: form.last_name,
          role_key: form.role_key,
          job_title: form.job_title,
          department_id: form.department_id || null,
          location: form.location,
        });
      }
      return endpoints.createEmployee({
        ...form,
        department_id: form.department_id || null,
      });
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["employees"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      if (mode === "invite" && res && typeof res === "object" && "invite_url" in res) {
        setInviteUrl((res as { invite_url: string }).invite_url);
        toast.success("Invite created — link copied");
        navigator.clipboard?.writeText((res as { invite_url: string }).invite_url).catch(() => undefined);
      } else {
        toast.success("Employee added");
        setOpen(false);
      }
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (!open) {
    return (
      <Button onClick={() => setOpen(true)} variant="primary">
        Add employee
      </Button>
    );
  }

  return (
    <form
      className="panel grid max-w-xl gap-2 p-4 sm:grid-cols-2"
      onSubmit={(e) => {
        e.preventDefault();
        create.mutate();
      }}
    >
      <div className="flex gap-2 sm:col-span-2">
        <Button type="button" variant={mode === "invite" ? "subtle" : "ghost"} onClick={() => setMode("invite")}>
          Invite link
        </Button>
        <Button type="button" variant={mode === "direct" ? "subtle" : "ghost"} onClick={() => setMode("direct")}>
          Create with password
        </Button>
      </div>
      <Input placeholder="First name" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} required />
      <Input placeholder="Last name" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
      <Input placeholder="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
      <Input placeholder="Job title" value={form.job_title} onChange={(e) => setForm({ ...form, job_title: e.target.value })} required />
      <Select value={form.role_key} onChange={(e) => setForm({ ...form, role_key: e.target.value })}>
        {Object.entries(ROLE_LABELS).map(([k, v]) => (
          <option key={k} value={k}>
            {v}
          </option>
        ))}
      </Select>
      <Select value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })}>
        <option value="">Department</option>
        {(depts.data || []).map((d) => (
          <option key={d.id} value={d.id}>
            {d.name}
          </option>
        ))}
      </Select>
      {mode === "direct" ? (
        <Input
          className="sm:col-span-2"
          placeholder="Temp password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          required
        />
      ) : null}
      {inviteUrl ? (
        <p className="break-all text-[11px] text-muted sm:col-span-2">
          Invite URL: <span className="text-ink">{inviteUrl}</span>
        </p>
      ) : null}
      <div className="flex gap-2 sm:col-span-2">
        <Button type="submit" loading={create.isPending}>
          {mode === "invite" ? "Send invite" : "Save"}
        </Button>
        <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
