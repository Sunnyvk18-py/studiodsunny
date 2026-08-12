"use client";

import { Button, Input, PageHeader, Skeleton } from "@/components/ui";
import { endpoints, CompanySettings } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";

export default function CompanySettingsPage() {
  const { can, user } = useAuth();
  const canEdit = can("settings:write") || user?.role_key === "founder";
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["company-settings"], queryFn: endpoints.companySettings });
  const [form, setForm] = useState<Partial<CompanySettings>>({});

  useEffect(() => {
    if (q.data) setForm(q.data);
  }, [q.data]);

  const save = useMutation({
    mutationFn: () =>
      endpoints.updateCompanySettings({
        name: form.name,
        legal_name: form.legal_name,
        billing_entity: form.billing_entity,
        public_site: form.public_site,
        hq_domain: form.hq_domain,
        client_portal_domain: form.client_portal_domain,
        careers_domain: form.careers_domain,
        timezone: form.timezone,
        currency: form.currency,
        notes: form.notes,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["company-settings"] });
      toast.success("Company settings saved");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (q.isLoading) return <Skeleton className="mx-auto h-64 max-w-2xl" />;

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader kicker="Company" title="Company settings" description="Legal name, billing entity, and HQ domains." />
      <form
        className="panel grid gap-3 p-5 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (canEdit) save.mutate();
        }}
      >
        {(
          [
            ["name", "Company"],
            ["legal_name", "Legal name"],
            ["billing_entity", "Billing entity"],
            ["public_site", "Public site"],
            ["hq_domain", "Employee HQ"],
            ["client_portal_domain", "Client portal"],
            ["careers_domain", "Careers"],
            ["timezone", "Timezone"],
            ["currency", "Currency"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="block text-[12px] text-muted">
            {label}
            <Input
              className="mt-1"
              value={(form[key] as string) || ""}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            />
          </label>
        ))}
        <label className="block text-[12px] text-muted sm:col-span-2">
          Notes
          <Input
            className="mt-1"
            value={form.notes || ""}
            disabled={!canEdit}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />
        </label>
        {canEdit ? (
          <div className="sm:col-span-2">
            <Button type="submit" loading={save.isPending}>
              Save
            </Button>
          </div>
        ) : (
          <p className="text-[12px] text-muted sm:col-span-2">Read-only for your role.</p>
        )}
      </form>
    </div>
  );
}
