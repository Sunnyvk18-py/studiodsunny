"use client";

import { PageHeader, Skeleton } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";

export default function DepartmentsPage() {
  const q = useQuery({ queryKey: ["departments"], queryFn: endpoints.departments });
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader kicker="Org" title="Departments" description="Founder, Operations, Sales, Engineering, Design, Automation, Marketing, Finance." />
      {q.isLoading ? (
        <Skeleton className="h-40" />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {(q.data || []).map((d) => (
            <div key={d.id} className="panel p-4">
              <p className="font-medium">{d.name}</p>
              <p className="mt-1 text-sm text-muted">{d.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
