"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState } from "react";
import { Toaster } from "sonner";
import { AuthProvider } from "@/lib/auth";
import { Observability } from "@/components/observability";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 20_000 },
        },
      }),
  );

  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
      <QueryClientProvider client={client}>
        <AuthProvider>
          <Observability />
          {children}
          <Toaster
            theme="system"
            position="bottom-right"
            toastOptions={{
              className:
                "!bg-[var(--bg-raised)] !text-[var(--ink)] !border-[var(--line)] !text-[13px] !shadow-none !rounded-lg",
            }}
          />
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
