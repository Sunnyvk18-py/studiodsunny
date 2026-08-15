import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
const isDev = process.env.NODE_ENV === "development";

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || process.env.NODE_ENV || "development",
    tracesSampleRate: isDev ? 0 : 0.1,
    sendDefaultPii: false,
    beforeSend(event) {
      if (event.user) {
        delete event.user.email;
        delete event.user.username;
        delete event.user.ip_address;
      }
      const headers = event.request?.headers;
      if (headers) {
        for (const key of Object.keys(headers)) {
          if (/authorization|cookie|csrf|token|session/i.test(key)) {
            headers[key] = "[Filtered]";
          }
        }
      }
      return event;
    },
  });
}
