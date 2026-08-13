"use client";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { Badge, Button, Input, PageHeader, Select, Skeleton } from "@/components/ui";
import { ROLE_LABELS, endpoints } from "@/lib/api";
import { formatINR, prettyStatus } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

export default function EmployeeProfilePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { user, can } = useAuth();
  const [editing, setEditing] = useState(false);
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    display_name: "",
    job_title: "",
    location: "",
    phone: "",
    availability: "available",
    role_key: "developer",
    department_id: "",
    is_active: true,
  });

  const emp = useQuery({ queryKey: ["employee", id], queryFn: () => endpoints.employee(id) });
  const depts = useQuery({ queryKey: ["departments"], queryFn: endpoints.departments });
  const tasks = useQuery({ queryKey: ["tasks", "emp", id], queryFn: () => endpoints.tasks(), enabled: !!emp.data });

  const isFounder = user?.role_key === "founder" || user?.is_superadmin;
  const isSelf = Boolean(user?.employee_id && user.employee_id === id);
  const canEdit = isFounder || isSelf;
  const inactive = emp.data ? !emp.data.is_active : false;

  useEffect(() => {
    if (!emp.data) return;
    setForm({
      first_name: emp.data.first_name,
      last_name: emp.data.last_name,
      display_name: emp.data.display_name,
      job_title: emp.data.job_title,
      location: emp.data.location || "",
      phone: emp.data.phone || "",
      availability: emp.data.availability,
      role_key: emp.data.role_key,
      department_id: emp.data.department_id || "",
      is_active: emp.data.is_active,
    });
  }, [emp.data]);

  const save = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = {
        first_name: form.first_name,
        last_name: form.last_name,
        display_name: form.display_name,
        job_title: form.job_title,
        location: form.location || null,
        phone: form.phone || null,
        availability: form.availability,
      };
      if (isFounder) {
        payload.role_key = form.role_key;
        payload.department_id = form.department_id || null;
        payload.is_active = form.is_active;
      }
      return endpoints.updateEmployee(id, payload);
    },
    onSuccess: (updated) => {
      qc.setQueryData(["employee", id], updated);
      qc.invalidateQueries({ queryKey: ["employees"] });
      setEditing(false);
      toast.success("Profile updated");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deactivate = useMutation({
    mutationFn: () => endpoints.deactivateEmployee(id),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ["employees"] });
      const previous = qc.getQueriesData({ queryKey: ["employees"] });
      qc.setQueriesData({ queryKey: ["employees"] }, (old: unknown) => {
        if (!Array.isArray(old)) return old;
        return old.filter((e: { id: string }) => e.id !== id);
      });
      return { previous };
    },
    onError: (e: Error, _v, ctx) => {
      ctx?.previous?.forEach(([key, data]) => qc.setQueryData(key, data));
      toast.error(e.message);
    },
    onSuccess: () => {
      toast.success("Employee deactivated");
      router.push("/team");
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["employees"] }),
  });

  if (emp.isLoading || !emp.data) return <Skeleton className="h-64" />;
  const e = emp.data;
  const mine = (tasks.data || []).filter((t) => t.assignee_id === e.user_id);
  const showComp = can("employees.compensation:read") || user?.id === e.user_id;

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        kicker={e.department_name || ROLE_LABELS[e.role_key]}
        title={e.display_name}
        description={`${e.job_title} · ${e.location || "—"}`}
        actions={
          <>
            {inactive ? <Badge tone="warn">Deactivated</Badge> : null}
            <Badge tone={e.availability === "busy" ? "warn" : "ok"}>{prettyStatus(e.availability)}</Badge>
            {canEdit && !inactive ? (
              <Button variant="outline" onClick={() => setEditing((v) => !v)}>
                {editing ? "Cancel edit" : "Edit"}
              </Button>
            ) : null}
            {isFounder && !inactive && !isSelf ? (
              <Button variant="outline" onClick={() => setConfirmDeactivate(true)}>
                Deactivate
              </Button>
            ) : null}
          </>
        }
      />

      {editing && !inactive ? (
        <form
          className="panel mb-6 space-y-4 p-5"
          onSubmit={(ev) => {
            ev.preventDefault();
            save.mutate();
          }}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="First name">
              <Input value={form.first_name} onChange={(ev) => setForm({ ...form, first_name: ev.target.value })} />
            </Field>
            <Field label="Last name">
              <Input value={form.last_name} onChange={(ev) => setForm({ ...form, last_name: ev.target.value })} />
            </Field>
            <Field label="Display name">
              <Input value={form.display_name} onChange={(ev) => setForm({ ...form, display_name: ev.target.value })} />
            </Field>
            <Field label="Job title">
              <Input value={form.job_title} onChange={(ev) => setForm({ ...form, job_title: ev.target.value })} />
            </Field>
            <Field label="Location">
              <Input value={form.location} onChange={(ev) => setForm({ ...form, location: ev.target.value })} />
            </Field>
            <Field label="Phone">
              <Input value={form.phone} onChange={(ev) => setForm({ ...form, phone: ev.target.value })} />
            </Field>
            <Field label="Availability">
              <Select value={form.availability} onChange={(ev) => setForm({ ...form, availability: ev.target.value })}>
                {["available", "busy", "away", "ooo"].map((s) => (
                  <option key={s} value={s}>
                    {prettyStatus(s)}
                  </option>
                ))}
              </Select>
            </Field>
            {isFounder ? (
              <>
                <Field label="Role">
                  <Select value={form.role_key} onChange={(ev) => setForm({ ...form, role_key: ev.target.value })}>
                    {Object.entries(ROLE_LABELS).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Department">
                  <Select
                    value={form.department_id}
                    onChange={(ev) => setForm({ ...form, department_id: ev.target.value })}
                  >
                    <option value="">No department</option>
                    {(depts.data || []).map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Active">
                  <Select
                    value={form.is_active ? "true" : "false"}
                    onChange={(ev) => setForm({ ...form, is_active: ev.target.value === "true" })}
                  >
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                  </Select>
                </Field>
              </>
            ) : null}
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={save.isPending}>
              Save changes
            </Button>
          </div>
        </form>
      ) : null}

      <div className="grid gap-3 md:grid-cols-4">
        <Stat label="Active projects" value={String(e.active_projects)} />
        <Stat label="Utilization" value={`${e.utilization}%`} gold />
        <Stat label="Leave balance" value={showComp ? `${e.leave_balance_days} days` : "—"} />
        <Stat label="Employment" value={prettyStatus(e.employment_type)} />
      </div>

      <section className="panel mt-6 p-5">
        <h2 className="section-title mb-3">Overview</h2>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <Row k="Email" v={e.email} />
          <Row k="Role" v={ROLE_LABELS[e.role_key]} />
          <Row k="Joined" v={e.joining_date || "—"} />
          {showComp ? (
            <Row
              k="Compensation"
              v={e.salary ? `${e.salary_currency} ${formatINR(Number(e.salary)).replace("₹", "")}/mo` : "—"}
            />
          ) : null}
          <Row k="Skills" v={e.skills?.join(", ") || "—"} />
        </dl>
        {!showComp ? <p className="mt-4 text-xs text-muted">Compensation is restricted.</p> : null}
      </section>

      <section className="mt-6">
        <h2 className="section-title mb-3">Tasks</h2>
        <div className="space-y-2">
          {mine.slice(0, 12).map((t) => (
            <div key={t.id} className="panel lift flex items-center justify-between p-3 text-sm">
              <span>{t.title}</span>
              <span className="text-xs text-muted">{prettyStatus(t.status)}</span>
            </div>
          ))}
        </div>
      </section>

      <ConfirmDialog
        open={confirmDeactivate}
        title={`Deactivate ${e.display_name}?`}
        body="Their account will be soft-deactivated and all refresh sessions revoked. They leave the default team list."
        confirmLabel="Deactivate"
        loading={deactivate.isPending}
        onCancel={() => setConfirmDeactivate(false)}
        onConfirm={() => deactivate.mutate()}
      />
    </div>
  );
}

function Stat({ label, value, gold }: { label: string; value: string; gold?: boolean }) {
  return (
    <div className="panel p-4">
      <p className="text-[12px] text-muted">{label}</p>
      <p className={`mt-1 text-[20px] font-semibold tabular-nums tracking-tight ${gold ? "gold-num" : ""}`}>{value}</p>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <dt className="text-muted">{k}</dt>
      <dd className="mt-0.5 text-ink">{v}</dd>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-muted">{label}</span>
      {children}
    </label>
  );
}
