"use client";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { Badge, Button, Input, PageHeader, Select, Skeleton, Textarea } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatINR, prettyStatus } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

const CLIENT_STATUSES = ["active", "prospect", "paused", "churned"];

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { can } = useAuth();
  const canWrite = can("clients:write");
  const [editing, setEditing] = useState(false);
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [form, setForm] = useState({
    business_name: "",
    primary_contact_name: "",
    email: "",
    phone: "",
    status: "active",
    notes: "",
  });

  const client = useQuery({ queryKey: ["client", id], queryFn: () => endpoints.client(id) });
  const projects = useQuery({
    queryKey: ["projects", "client", id],
    queryFn: () => endpoints.projects({ client_id: id }),
    enabled: !client.data?.archived,
  });

  useEffect(() => {
    if (!client.data) return;
    setForm({
      business_name: client.data.business_name,
      primary_contact_name: client.data.primary_contact_name || "",
      email: client.data.email || "",
      phone: client.data.phone || "",
      status: client.data.status,
      notes: client.data.notes || "",
    });
  }, [client.data]);

  const save = useMutation({
    mutationFn: () =>
      endpoints.updateClient(id, {
        business_name: form.business_name,
        primary_contact_name: form.primary_contact_name || null,
        email: form.email || null,
        phone: form.phone || null,
        status: form.status,
        notes: form.notes || null,
      }),
    onSuccess: (updated) => {
      qc.setQueryData(["client", id], updated);
      qc.invalidateQueries({ queryKey: ["clients"] });
      setEditing(false);
      toast.success("Client updated");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const archive = useMutation({
    mutationFn: () => endpoints.archiveClient(id),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ["clients"] });
      const previous = qc.getQueriesData({ queryKey: ["clients"] });
      qc.setQueriesData({ queryKey: ["clients"] }, (old: unknown) => {
        if (!Array.isArray(old)) return old;
        return old.filter((c: { id: string }) => c.id !== id);
      });
      return { previous };
    },
    onError: (e: Error, _v, ctx) => {
      ctx?.previous?.forEach(([key, data]) => qc.setQueryData(key, data));
      toast.error(e.message);
    },
    onSuccess: () => {
      toast.success("Client archived");
      router.push("/clients");
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["clients"] }),
  });

  if (client.isLoading || !client.data) return <Skeleton className="h-64" />;
  const c = client.data;
  const stepPct = Math.round(((c.onboarding_complete ? 8 : c.onboarding_step) / 8) * 100);
  const archived = Boolean(c.archived);

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        kicker={c.industry || "Client"}
        title={c.business_name}
        description={c.notes || `${c.primary_contact_name || ""} · ${c.location || ""}`}
        actions={
          <>
            {archived ? <Badge tone="warn">Archived</Badge> : null}
            {!archived && canWrite ? (
              <>
                <Button variant="outline" onClick={() => setEditing((v) => !v)}>
                  {editing ? "Cancel edit" : "Edit"}
                </Button>
                <Button variant="outline" onClick={() => setConfirmArchive(true)}>
                  Archive
                </Button>
              </>
            ) : null}
            {!archived ? (
              <Link href={`/projects/new?client=${c.id}`}>
                <Button>New project</Button>
              </Link>
            ) : null}
          </>
        }
      />

      {editing && !archived ? (
        <form
          className="panel mb-6 space-y-4 p-5"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Business name">
              <Input
                required
                value={form.business_name}
                onChange={(e) => setForm({ ...form, business_name: e.target.value })}
              />
            </Field>
            <Field label="Primary contact">
              <Input
                value={form.primary_contact_name}
                onChange={(e) => setForm({ ...form, primary_contact_name: e.target.value })}
              />
            </Field>
            <Field label="Email">
              <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </Field>
            <Field label="Phone">
              <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </Field>
            <Field label="Status">
              <Select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                {CLIENT_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {prettyStatus(s)}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <Field label="Notes">
            <Textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </Field>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={save.isPending}>
              Save changes
            </Button>
          </div>
        </form>
      ) : (
        <div className="grid gap-4 md:grid-cols-4">
          <Info label="Contact" value={c.primary_contact_name || "—"} />
          <Info label="Email" value={c.email || "—"} />
          <Info label="Phone" value={c.phone || "—"} />
          <Info label="Status" value={prettyStatus(c.status)} />
        </div>
      )}

      <section className="panel mt-6 p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="section-title">Onboarding</h2>
          <span className="gold-num text-[13px] font-semibold">{stepPct}%</span>
        </div>
        <div className="progress-track h-1.5">
          <div className="progress-fill" style={{ width: `${stepPct}%` }} />
        </div>
        <ol className="mt-4 grid gap-2 text-sm md:grid-cols-4">
          {["Company details", "Requirements", "Brand assets", "Content", "Technical", "Domain / hosting", "Approvals", "Kickoff"].map(
            (s, i) => (
              <li key={s} className={i < c.onboarding_step || c.onboarding_complete ? "text-ink" : "text-muted"}>
                {i + 1}. {s}
              </li>
            ),
          )}
        </ol>
      </section>

      <section className="mt-6">
        <h2 className="section-title mb-2">Projects</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {(projects.data || []).map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`} className="panel lift p-4">
              <div className="flex justify-between">
                <p className="font-medium">{p.name}</p>
                <Badge>{prettyStatus(p.status)}</Badge>
              </div>
              <p className="mt-2 text-xs text-muted">
                {p.progress}% · {p.project_type}
              </p>
            </Link>
          ))}
        </div>
      </section>

      {c.pending_invoices ? (
        <p className="mt-6 text-sm text-warn">Pending invoices: {formatINR(Number(c.pending_invoices))}</p>
      ) : null}

      <ConfirmDialog
        open={confirmArchive}
        title={`Archive ${c.business_name}?`}
        body="It will leave the default client list. You can find it again with the Archived filter."
        confirmLabel="Archive"
        loading={archive.isPending}
        onCancel={() => setConfirmArchive(false)}
        onConfirm={() => archive.mutate()}
      />
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="panel p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-sm">{value}</p>
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
