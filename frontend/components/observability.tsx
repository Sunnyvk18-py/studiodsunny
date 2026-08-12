"use client";

import { useEffect } from "react";
import posthog from "posthog-js";
import * as Sentry from "@sentry/react";

export function Observability() {
  useEffect(() => {
    const posthogKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    if (posthogKey && typeof window !== "undefined") {
      posthog.init(posthogKey, {
        api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com",
        capture_pageview: true,
        persistence: "localStorage",
      });
    }

    const sentryDsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
    if (sentryDsn) {
      Sentry.init({
        dsn: sentryDsn,
        environment: process.env.NODE_ENV,
        tracesSampleRate: 0.1,
      });
    }
  }, []);

  return null;
}
