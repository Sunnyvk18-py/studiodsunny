"use client";

import { Mark } from "@/components/mark";
import { Button, Input } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { endpoints, setCsrfToken } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { toast } from "sonner";

export default function LoginPage() {
  return (
    <Suspense>
      <LoginInner />
    </Suspense>
  );
}

function LoginInner() {
  const { user, loading, setUser } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [tempToken, setTempToken] = useState<string | null>(params.get("temp"));
  const [code, setCode] = useState("");
  const [google, setGoogle] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/home");
  }, [loading, user, router]);

  useEffect(() => {
    endpoints.authProviders().then((p) => setGoogle(p.google)).catch(() => setGoogle(false));
    if (params.get("totp") === "1" && params.get("temp")) {
      setTempToken(params.get("temp"));
    }
  }, [params]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (tempToken) {
        const res = await endpoints.verify2fa(tempToken, code);
        if (res.user) {
          setCsrfToken(res.csrf_token);
          setUser(res.user);
          toast.success(`Welcome back, ${res.user.first_name}.`);
          router.push("/home");
        }
        return;
      }
      const res = await endpoints.login(email, password);
      if (res.needs_2fa && res.temp_token) {
        setTempToken(res.temp_token);
        toast.message("Enter your authenticator code");
        return;
      }
      if (res.user) {
        setCsrfToken(res.csrf_token);
        setUser(res.user);
        toast.success(`Welcome back, ${res.user.first_name}.`);
        router.push("/home");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Unable to sign in");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="dark auth-wash relative min-h-dvh overflow-hidden text-ink">
      <div className="relative mx-auto grid min-h-dvh max-w-6xl items-center gap-16 px-6 py-16 lg:grid-cols-[1.05fr_0.95fr]">
        <div>
          <div className="mb-10 flex items-center gap-3">
            <Mark className="size-11" />
            <div>
              <p className="kicker">Studio Sunny</p>
              <p className="text-[15px] font-semibold tracking-tight">HQ · Company OS</p>
            </div>
          </div>
          <h1 className="font-display text-[52px] leading-[1.05] md:text-[60px]">
            Operate the
            <br />
            whole company
            <br />
            from one room.
          </h1>
          <p className="mt-5 max-w-md text-[15px] leading-7 text-muted">
            Projects, people, clients, and cash — with the calm of a private banking OS.
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          className="panel p-8"
          style={{ boxShadow: "0 8px 24px rgba(0,0,0,0.35)" }}
        >
          <p className="kicker">Sign in</p>
          <h2 className="mt-2 font-display text-[32px] leading-none">{tempToken ? "Authenticator" : "Enter HQ"}</h2>

          {tempToken ? (
            <>
              <label className="mt-8 block text-[12px] font-medium text-muted">6-digit code</label>
              <Input className="mt-2" value={code} onChange={(e) => setCode(e.target.value)} placeholder="123456" autoFocus />
              <Button type="submit" className="mt-6 w-full" loading={submitting}>
                Verify
              </Button>
              <button type="button" className="mt-3 text-[12px] text-muted" onClick={() => setTempToken(null)}>
                Back to password
              </button>
            </>
          ) : (
            <>
              <label className="mt-8 block text-[12px] font-medium text-muted" htmlFor="hq-email">
                Email
              </label>
              <Input id="hq-email" className="mt-2" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
              <label className="mt-4 block text-[12px] font-medium text-muted" htmlFor="hq-password">
                Password
              </label>
              <Input
                id="hq-password"
                className="mt-2"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
              <Button type="submit" className="mt-6 w-full" loading={submitting}>
                Sign in
              </Button>
              <a href="/forgot-password" className="mt-3 block text-center text-[12px] text-accent hover:underline">
                Forgot password?
              </a>
              {google ? (
                <a
                  href={endpoints.googleStartUrl()}
                  className="mt-3 flex h-10 w-full items-center justify-center rounded-md border border-line text-[14px] text-ink hover:bg-sunken"
                >
                  Continue with Google
                </a>
              ) : null}
            </>
          )}
        </form>
      </div>
    </div>
  );
}
