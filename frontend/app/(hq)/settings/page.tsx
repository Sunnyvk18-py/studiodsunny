"use client";

import { Button, Input, PageHeader } from "@/components/ui";
import { ROLE_LABELS, endpoints, setCsrfToken } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

export default function SettingsPage() {
  const { user, setUser } = useAuth();
  const [code, setCode] = useState("");
  const [setupUrl, setSetupUrl] = useState<string | null>(null);
  const [secret, setSecret] = useState<string | null>(null);

  const providers = useQuery({
    queryKey: ["auth-providers"],
    queryFn: endpoints.authProviders,
  });

  const setup = useMutation({
    mutationFn: () => endpoints.setup2fa(),
    onSuccess: (res) => {
      setSetupUrl(res.otpauth_url);
      setSecret(res.secret);
      toast.success("Scan the secret in your authenticator app");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const enable = useMutation({
    mutationFn: () => endpoints.enable2fa(code),
    onSuccess: (res) => {
      if (res.user) {
        setCsrfToken(res.csrf_token);
        setUser(res.user);
      }
      setCode("");
      toast.success("Two-factor enabled");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const disable = useMutation({
    mutationFn: () => endpoints.disable2fa(code),
    onSuccess: (res) => {
      if (res.user) setUser(res.user);
      setCode("");
      setSetupUrl(null);
      setSecret(null);
      toast.success("Two-factor disabled");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader kicker="Account" title="Settings" description="Profile, security, and sign-in providers." />
      <div className="panel mb-4 space-y-3 p-5 text-sm">
        <Row k="Name" v={user?.display_name || ""} />
        <Row k="Email" v={user?.email || ""} />
        <Row k="Role" v={ROLE_LABELS[user?.role_key || ""] || user?.role_key || ""} />
        <p className="pt-2 text-xs text-muted">Theme toggle lives in the top bar.</p>
      </div>

      <div className="panel space-y-4 p-5">
        <div>
          <p className="text-[14px] font-semibold">Two-factor authentication</p>
          <p className="mt-1 text-[13px] text-muted">
            TOTP via any authenticator app. {user?.totp_enabled ? "Currently enabled." : "Currently off."}
          </p>
        </div>
        {!user?.totp_enabled ? (
          <>
            <Button onClick={() => setup.mutate()} loading={setup.isPending} variant="outline">
              Generate secret
            </Button>
            {secret ? (
              <div className="rounded-md border border-line bg-sunken/40 p-3 text-[12px]">
                <p className="text-muted">Secret</p>
                <p className="mt-1 break-all font-mono text-ink">{secret}</p>
                {setupUrl ? (
                  <p className="mt-2 break-all text-muted">
                    otpauth: <span className="text-ink">{setupUrl}</span>
                  </p>
                ) : null}
              </div>
            ) : null}
            <div className="flex flex-wrap gap-2">
              <Input className="max-w-[160px]" placeholder="123456" value={code} onChange={(e) => setCode(e.target.value)} />
              <Button onClick={() => enable.mutate()} loading={enable.isPending} disabled={code.length < 6}>
                Enable 2FA
              </Button>
            </div>
          </>
        ) : (
          <div className="flex flex-wrap gap-2">
            <Input className="max-w-[160px]" placeholder="123456" value={code} onChange={(e) => setCode(e.target.value)} />
            <Button variant="danger" onClick={() => disable.mutate()} loading={disable.isPending} disabled={code.length < 6}>
              Disable 2FA
            </Button>
          </div>
        )}
      </div>

      <div className="panel mt-4 space-y-2 p-5">
        <p className="text-[14px] font-semibold">SSO</p>
        <p className="text-[13px] text-muted">
          Google Workspace OIDC is {providers.data?.google ? "configured" : "not configured on this API"}.
        </p>
      </div>

      <ChangePasswordCard />
    </div>
  );
}

function ChangePasswordCard() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const mut = useMutation({
    mutationFn: () => endpoints.changePassword(current, next),
    onSuccess: () => {
      setCurrent("");
      setNext("");
      toast.success("Password updated");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="panel mt-4 space-y-3 p-5">
      <div>
        <p className="text-[14px] font-semibold">Password</p>
        <p className="mt-1 text-[13px] text-muted">Change the password for this account.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Input
          type="password"
          className="max-w-[200px]"
          placeholder="Current"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
        />
        <Input
          type="password"
          className="max-w-[200px]"
          placeholder="New (8+)"
          value={next}
          onChange={(e) => setNext(e.target.value)}
        />
        <Button
          onClick={() => mut.mutate()}
          loading={mut.isPending}
          disabled={current.length < 6 || next.length < 8}
        >
          Update password
        </Button>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between border-b border-line py-2">
      <span className="text-muted">{k}</span>
      <span>{v}</span>
    </div>
  );
}
