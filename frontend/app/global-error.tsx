"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en">
      <body className="min-h-screen bg-[#12121a] text-[#f4f1ea]">
        <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center gap-4 px-6">
          <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-[#e8b86d]">Something broke</p>
          <h1 className="text-[28px] font-semibold tracking-tight">HQ hit an unexpected error.</h1>
          <p className="text-[14px] text-[#a39e93]">
            Your work in memory may still be recoverable. Try again, or return home and reopen the page.
          </p>
          <div className="flex flex-wrap gap-2 pt-2">
            <button
              type="button"
              onClick={() => reset()}
              className="rounded-lg bg-[#e8b86d] px-4 py-2 text-[13px] font-semibold text-[#12121a]"
            >
              Try again
            </button>
            <a
              href="/home"
              className="rounded-lg border border-[#2a2833] px-4 py-2 text-[13px] font-semibold text-[#f4f1ea]"
            >
              Go to Home
            </a>
          </div>
          {error.digest ? <p className="text-[11px] text-[#6f6a62]">Ref {error.digest}</p> : null}
        </div>
      </body>
    </html>
  );
}
