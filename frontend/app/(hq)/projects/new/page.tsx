"use client";

import { Button, Input, PageHeader, Select, Textarea } from "@/components/ui";
import { PROJECT_TYPES, endpoints } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

const STEPS = ["Client", "Type", "Details", "Timeline", "Team", "Budget", "Review"];

export default function NewProjectPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    client_id: "",
    project_type: "Website",
    name: "",
    description: "",
    start_date: "",
    target_completion_date: "",
    project_manager_id: "",
    member_ids: [] as string[],
    budget: "",
    budget_currency: "INR",
    priority: "medium",
    tech_stack: "",
  });

  const clients = useQuery({ queryKey: ["clients"], queryFn: () => endpoints.clients() });
  const people = useQuery({ queryKey: ["employees"], queryFn: () => endpoints.employees() });

  const create = useMutation({
    mutationFn: () =>
      endpoints.createProject({
        client_id: form.client_id,
        project_type: form.project_type,
        name: form.name,
        description: form.description || null,
        start_date: form.start_date || null,
        target_completion_date: form.target_completion_date || null,
        project_manager_id: form.project_manager_id || null,
        member_ids: form.member_ids,
        budget: form.budget ? Number(form.budget) : null,
        budget_currency: form.budget_currency,
        priority: form.priority,
        tech_stack: form.tech_stack
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      }),
    onSuccess: async (project) => {
      await qc.invalidateQueries({ queryKey: ["projects"] });
      await qc.invalidateQueries({ queryKey: ["dashboard"] });
      await qc.invalidateQueries({ queryKey: ["activity"] });
      toast.success("Project created");
      router.push(`/projects/${project.id}`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function next() {
    if (step === 0 && !form.client_id) return toast.error("Select a client");
    if (step === 2 && form.name.trim().length < 2) return toast.error("Give the project a name");
    if (step < STEPS.length - 1) setStep(step + 1);
    else create.mutate();
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader kicker="New engagement" title="Create project" description="Seven quiet steps. No clutter." />

      <div className="mb-8 flex gap-2 overflow-x-auto pb-1">
        {STEPS.map((s, i) => (
          <button
            key={s}
            onClick={() => setStep(i)}
            className={`rounded-full px-3 py-1 text-xs ${i === step ? "bg-accent text-accent-fg" : i < step ? "bg-sunken text-ink" : "text-muted"}`}
          >
            {i + 1}. {s}
          </button>
        ))}
      </div>

      <div className="panel p-6">
        {step === 0 && (
          <Field label="Client">
            <Select value={form.client_id} onChange={(e) => setForm({ ...form, client_id: e.target.value })}>
              <option value="">Select client</option>
              {(clients.data || []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.business_name}
                </option>
              ))}
            </Select>
            <p className="mt-2 text-xs text-muted">
              Need someone new?{" "}
              <Link href="/clients/new" className="text-accent hover:underline">
                Add a client first
              </Link>
              .
            </p>
          </Field>
        )}
        {step === 1 && (
          <Field label="Project type">
            <div className="grid gap-2 sm:grid-cols-2">
              {PROJECT_TYPES.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setForm({ ...form, project_type: t })}
                  className={`rounded-xl border px-3 py-3 text-left text-sm ${form.project_type === t ? "border-accent bg-sunken" : "border-line hover:bg-sunken"}`}
                >
                  {t}
                </button>
              ))}
            </div>
          </Field>
        )}
        {step === 2 && (
          <div className="space-y-4">
            <Field label="Project name">
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Muttonly Commerce Platform" />
            </Field>
            <Field label="Description">
              <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </Field>
            <Field label="Priority">
              <Select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                {["low", "medium", "high", "urgent"].map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Tech stack (comma separated)">
              <Input value={form.tech_stack} onChange={(e) => setForm({ ...form, tech_stack: e.target.value })} placeholder="Next.js, FastAPI, PostgreSQL" />
            </Field>
          </div>
        )}
        {step === 3 && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Start date">
              <Input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
            </Field>
            <Field label="Target completion">
              <Input type="date" value={form.target_completion_date} onChange={(e) => setForm({ ...form, target_completion_date: e.target.value })} />
            </Field>
          </div>
        )}
        {step === 4 && (
          <div className="space-y-4">
            <Field label="Project manager">
              <Select value={form.project_manager_id} onChange={(e) => setForm({ ...form, project_manager_id: e.target.value })}>
                <option value="">Unassigned</option>
                {(people.data || []).map((e) => (
                  <option key={e.user_id} value={e.user_id}>
                    {e.display_name} · {e.job_title}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Team">
              <div className="grid max-h-64 gap-2 overflow-y-auto">
                {(people.data || []).map((e) => {
                  const checked = form.member_ids.includes(e.user_id);
                  return (
                    <label key={e.id} className="flex items-center gap-3 rounded-xl border border-line px-3 py-2 text-sm">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() =>
                          setForm({
                            ...form,
                            member_ids: checked
                              ? form.member_ids.filter((id) => id !== e.user_id)
                              : [...form.member_ids, e.user_id],
                          })
                        }
                      />
                      {e.display_name}
                      <span className="text-xs text-muted">{e.job_title}</span>
                    </label>
                  );
                })}
              </div>
            </Field>
          </div>
        )}
        {step === 5 && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Budget">
              <Input type="number" value={form.budget} onChange={(e) => setForm({ ...form, budget: e.target.value })} placeholder="145000" />
            </Field>
            <Field label="Currency">
              <Select value={form.budget_currency} onChange={(e) => setForm({ ...form, budget_currency: e.target.value })}>
                <option>INR</option>
                <option>USD</option>
              </Select>
            </Field>
          </div>
        )}
        {step === 6 && (
          <div className="space-y-2 text-sm">
            <Row k="Client" v={clients.data?.find((c) => c.id === form.client_id)?.business_name || "—"} />
            <Row k="Type" v={form.project_type} />
            <Row k="Name" v={form.name || "—"} />
            <Row k="Timeline" v={`${form.start_date || "TBD"} → ${form.target_completion_date || "TBD"}`} />
            <Row k="Budget" v={form.budget ? `${form.budget_currency} ${form.budget}` : "—"} />
            <Row k="Team" v={`${form.member_ids.length} people`} />
          </div>
        )}

        <div className="mt-8 flex justify-between">
          <Button variant="ghost" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>
            Back
          </Button>
          <Button onClick={next} loading={create.isPending}>
            {step === STEPS.length - 1 ? "Create project" : "Continue"}
          </Button>
        </div>
      </div>
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

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-line py-2">
      <span className="text-muted">{k}</span>
      <span className="text-right text-ink">{v}</span>
    </div>
  );
}
