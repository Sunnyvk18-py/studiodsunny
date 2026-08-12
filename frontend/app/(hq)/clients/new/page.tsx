"use client";

import { Button, Input, PageHeader, Select, Textarea } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { toast } from "sonner";

export default function NewClientPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    business_name: "",
    primary_contact_name: "",
    email: "",
    phone: "",
    whatsapp: "",
    location: "",
    website: "",
    industry: "",
    lead_source: "Inbound website",
    notes: "",
  });

  const create = useMutation({
    mutationFn: () => endpoints.createClient(form),
    onSuccess: async (client) => {
      await qc.invalidateQueries({ queryKey: ["clients"] });
      await qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(`${client.business_name} added`);
      router.push(`/clients/${client.id}`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader kicker="New account" title="Add client" description="This becomes the commercial home for every project that follows." />
      <form onSubmit={onSubmit} className="panel space-y-4 p-6">
        <Field label="Business name">
          <Input required value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Primary contact">
            <Input value={form.primary_contact_name} onChange={(e) => setForm({ ...form, primary_contact_name: e.target.value })} />
          </Field>
          <Field label="Email">
            <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </Field>
          <Field label="Phone">
            <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </Field>
          <Field label="WhatsApp">
            <Input value={form.whatsapp} onChange={(e) => setForm({ ...form, whatsapp: e.target.value })} />
          </Field>
          <Field label="Location">
            <Input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
          </Field>
          <Field label="Website">
            <Input value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} />
          </Field>
          <Field label="Industry">
            <Input value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} />
          </Field>
          <Field label="Lead source">
            <Select value={form.lead_source} onChange={(e) => setForm({ ...form, lead_source: e.target.value })}>
              {["Inbound website", "Referral", "LinkedIn", "Cold outreach", "Conference", "Other"].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </Select>
          </Field>
        </div>
        <Field label="Notes">
          <Textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </Field>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button type="submit" loading={create.isPending}>
            Create client
          </Button>
        </div>
      </form>
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
