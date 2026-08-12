"use client";

import { Mark } from "@/components/mark";
import { Button, Input } from "@/components/ui";
import { endpoints } from "@/lib/api";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { toast } from "sonner";

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetInner />
    </Suspense>
  );
}

function ResetInner() {
  const params = useSearchParams();
  const token = params.get("token") || "";
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) {
      toast.error("Missing reset token");
      return;
    }
    setSubmitting(true);
    try {
      await endpoints.resetPassword(token, password);
      toast.success("Password updated — sign in");
      router.push("/login");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Reset failed");
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
            <p className="text-[12px] text-muted">Reset password</p>
          </div>
        </div>
        <form className="panel space-y-3 p-5" onSubmit={onSubmit}>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="New password (8+)"
            required
            minLength={8}
          />
          <Button type="submit" className="w-full" loading={submitting} disabled={!token}>
            Update password
          </Button>
          <Link href="/login" className="block text-center text-[12px] text-accent hover:underline">
            Back to sign in
          </Link>
        </form>
      </div>
    </div>
  );
}
