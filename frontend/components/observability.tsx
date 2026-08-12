"use client";

import { useEffect } from "react";
import posthog from "posthog-js";
import * as Sentry from "@sentry/nextjs";
import { useAuth } from "@/lib/auth";

export function Observability() {
  const { user } = useAuth();

  useEffect(() => {
    const posthogKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    if (posthogKey && typeof window !== "undefined") {
      posthog.init(posthogKey, {
        api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com",
        capture_pageview: true,
        persistence: "localStorage",
      });
    }
  }, []);

  useEffect(() => {
    if (!process.env.NEXT_PUBLIC_SENTRY_DSN) return;
    if (user?.role_key) {
      Sentry.setTag("user.role", user.role_key);
      Sentry.setTag("environment", process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || process.env.NODE_ENV || "development");
    } else {
      Sentry.setTag("user.role", "anonymous");
    }
  }, [user?.role_key]);

  return null;
}
