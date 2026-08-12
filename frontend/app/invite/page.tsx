"use client";

import { Mark } from "@/components/mark";
import { Button, Input } from "@/components/ui";
import { endpoints, setCsrfToken } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { toast } from "sonner";

export default function InvitePage() {
  return (
    <Suspense>
      <InviteInner />
    </Suspense>
  );
}

function InviteInner() {
  const params = useSearchParams();
  const token = params.get("token") || "";
  const router = useRouter();
  const { setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [first, setFirst] = useState("");
  const [last, setLast] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    endpoints
      .peekInvite(token)
      .then((r) => {
        setEmail(r.email);
        setFirst(r.first_name);
        setLast(r.last_name);
      })
      .catch((e: Error) => toast.error(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await endpoints.acceptInvite({
        token,
        password,
        first_name: first,
        last_name: last,
      });
      if (res.user) {
        setCsrfToken(res.csrf_token);
        setUser(res.user);
        toast.success("Welcome to Studio Sunny HQ");
        router.push("/home");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Invite failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="dark auth-wash relative min-h-dvh text-ink">
      <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-16">
        <div className="mb-8 flex items-center gap-3">
          <Mark className="size-10" />
          <div>
            <p className="text-[15px] font-semibold">Studio Sunny HQ</p>
            <p className="text-[12px] text-muted">Accept invite</p>
          </div>
        </div>
        {!token || loading ? (
          <p className="text-[13px] text-muted">{token ? "Loading invite…" : "Missing invite token."}</p>
        ) : (
          <form className="panel space-y-3 p-5" onSubmit={onSubmit}>
            <p className="text-[13px] text-muted">
              Join as <span className="text-ink">{email}</span>
            </p>
            <Input value={first} onChange={(e) => setFirst(e.target.value)} placeholder="First name" required />
            <Input value={last} onChange={(e) => setLast(e.target.value)} placeholder="Last name" />
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Choose a password (8+)"
              required
              minLength={8}
            />
            <Button type="submit" className="w-full" loading={submitting}>
              Activate account
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
