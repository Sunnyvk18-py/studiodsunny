"use client";

import { Mark } from "@/components/mark";
import { Button, Input } from "@/components/ui";
import { endpoints } from "@/lib/api";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { toast } from "sonner";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [devUrl, setDevUrl] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setDevUrl(null);
    try {
      const res = await endpoints.forgotPassword(email);
      toast.success(res.message);
      if (res.reset_url) setDevUrl(res.reset_url);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Request failed");
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
            <p className="text-[12px] text-muted">Forgot password</p>
          </div>
        </div>
        <form className="panel space-y-3 p-5" onSubmit={onSubmit}>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Work email" required />
          <Button type="submit" className="w-full" loading={submitting}>
            Send reset link
          </Button>
          {devUrl ? (
            <p className="break-all text-[11px] text-muted">
              Dev reset URL:{" "}
              <Link href={devUrl} className="text-accent hover:underline">
                {devUrl}
              </Link>
            </p>
          ) : null}
          <Link href="/login" className="block text-center text-[12px] text-accent hover:underline">
            Back to sign in
          </Link>
        </form>
      </div>
    </div>
  );
}
