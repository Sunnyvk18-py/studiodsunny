"use client";

import { Badge, Button, PageHeader, Skeleton, priorityTone } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { prettyStatus } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import {
  addDays,
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  startOfMonth,
  startOfWeek,
  subMonths,
} from "date-fns";
import Link from "next/link";
import { useMemo, useState } from "react";

export type CalendarEvent = {
  id: string;
  title: string;
  date: string;
  kind: string;
  status?: string | null;
  project_id?: string | null;
  project_name?: string | null;
  href?: string | null;
  priority?: string | null;
};

export default function CalendarPage() {
  const [cursor, setCursor] = useState(() => startOfMonth(new Date()));
  const [mine, setMine] = useState(false);
  const [selected, setSelected] = useState<Date>(() => new Date());

  const rangeStart = startOfWeek(startOfMonth(cursor));
  const rangeEnd = endOfWeek(endOfMonth(cursor));

  const events = useQuery({
    queryKey: ["calendar", format(rangeStart, "yyyy-MM-dd"), format(rangeEnd, "yyyy-MM-dd"), mine],
    queryFn: () =>
      endpoints.calendarEvents({
        start: format(rangeStart, "yyyy-MM-dd"),
        end: format(rangeEnd, "yyyy-MM-dd"),
        ...(mine ? { mine: "true" } : {}),
      }),
  });

  const days = useMemo(
    () => eachDayOfInterval({ start: rangeStart, end: rangeEnd }),
    [rangeStart, rangeEnd],
  );

  const byDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const ev of events.data || []) {
      const key = ev.date.slice(0, 10);
      const list = map.get(key) || [];
      list.push(ev);
      map.set(key, list);
    }
    return map;
  }, [events.data]);

  const selectedKey = format(selected, "yyyy-MM-dd");
  const agenda = byDay.get(selectedKey) || [];

  return (
    <div className="mx-auto max-w-[1200px]">
      <PageHeader
        kicker="Schedule"
        title="Calendar"
        description="Deadlines and milestones on one month grid."
        actions={
          <>
            <Button variant={mine ? "primary" : "outline"} onClick={() => setMine((v) => !v)}>
              {mine ? "Mine" : "Team"}
            </Button>
            <Button variant="outline" onClick={() => setCursor(startOfMonth(new Date()))}>
              Today
            </Button>
          </>
        }
      />

      <div className="mb-4 flex items-center justify-between">
        <Button variant="ghost" onClick={() => setCursor((c) => subMonths(c, 1))}>
          ←
        </Button>
        <h2 className="text-[18px] font-semibold tracking-tight">{format(cursor, "MMMM yyyy")}</h2>
        <Button variant="ghost" onClick={() => setCursor((c) => addMonths(c, 1))}>
          →
        </Button>
      </div>

      {events.isLoading ? (
        <Skeleton className="h-96" />
      ) : (
        <div className="grid gap-5 lg:grid-cols-[1.4fr_0.8fr]">
          <div className="panel overflow-hidden">
            <div className="grid grid-cols-7 border-b border-line text-[11px] uppercase tracking-[0.12em] text-muted">
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
                <div key={d} className="px-2 py-2 text-center">
                  {d}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7">
              {days.map((day) => {
                const key = format(day, "yyyy-MM-dd");
                const dayEvents = byDay.get(key) || [];
                const inMonth = isSameMonth(day, cursor);
                const active = isSameDay(day, selected);
                const today = isSameDay(day, new Date());
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setSelected(day)}
                    className={`min-h-[92px] border-b border-r border-line p-2 text-left transition ${
                      active ? "bg-accent/10" : "hover:bg-sunken/50"
                    } ${!inMonth ? "opacity-40" : ""}`}
                  >
                    <span
                      className={`inline-flex size-6 items-center justify-center rounded-full text-[12px] ${
                        today ? "bg-accent text-accent-fg" : "text-ink"
                      }`}
                    >
                      {format(day, "d")}
                    </span>
                    <div className="mt-1 space-y-0.5">
                      {dayEvents.slice(0, 3).map((ev) => (
                        <p key={ev.id} className="truncate text-[11px] text-muted">
                          <span className={ev.kind === "milestone" ? "text-[var(--accent-2)]" : "text-accent"}>•</span>{" "}
                          {ev.title}
                        </p>
                      ))}
                      {dayEvents.length > 3 ? (
                        <p className="text-[10px] text-muted">+{dayEvents.length - 3} more</p>
                      ) : null}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="panel p-4">
            <p className="kicker mb-2">Agenda</p>
            <p className="mb-4 text-[16px] font-semibold">{format(selected, "EEE, MMM d")}</p>
            {!agenda.length ? (
              <p className="text-[13px] text-muted">Nothing due this day.</p>
            ) : (
              <ul className="space-y-3">
                {agenda.map((ev) => (
                  <li key={ev.id} className="border-b border-line pb-3 last:border-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={ev.kind === "milestone" ? "info" : "accent"}>{ev.kind}</Badge>
                      {ev.priority ? <Badge tone={priorityTone(ev.priority)}>{ev.priority}</Badge> : null}
                      {ev.status ? <Badge>{prettyStatus(ev.status)}</Badge> : null}
                    </div>
                    <p className="mt-1 text-[14px] font-medium">{ev.title}</p>
                    <p className="text-[12px] text-muted">{ev.project_name || "Company"}</p>
                    {ev.href ? (
                      <Link href={ev.href} className="mt-1 inline-block text-[12px] text-muted hover:text-ink">
                        Open →
                      </Link>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
            <button
              type="button"
              className="mt-4 text-[12px] text-muted hover:text-ink"
              onClick={() => setSelected(addDays(selected, 1))}
            >
              Next day →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
