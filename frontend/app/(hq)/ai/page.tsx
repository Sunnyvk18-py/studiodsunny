"use client";

import { Button, PageHeader, Textarea } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { useMutation } from "@tanstack/react-query";
import { Bot } from "lucide-react";
import { useState } from "react";

const SUGGESTIONS = [
  "What should I focus on today?",
  "Which projects are behind schedule?",
  "What is the status of Muttonly?",
  "Who has availability this week?",
  "Which clients haven't paid?",
  "Show all urgent tasks.",
  "Prepare today's founder briefing.",
];

export default function SunnyAIPage() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<{ q: string; a: string }[]>([]);
  const ask = useMutation({
    mutationFn: (q: string) => endpoints.askAi(q),
    onSuccess: (res, q) => setHistory((h) => [{ q, a: res.answer }, ...h]),
  });

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        kicker="Intelligence"
        title="Sunny AI"
        description="Asks only what your role is allowed to see. No salary leaks for developers."
      />
      <div className="mb-4 flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => {
              setQuestion(s);
              ask.mutate(s);
            }}
            className="rounded-full border border-line bg-raised px-3 py-1.5 text-[12px] hover:border-accent/40 hover:text-accent"
          >
            {s}
          </button>
        ))}
      </div>
      <form
        className="panel p-5"
        onSubmit={(e) => {
          e.preventDefault();
          if (!question.trim()) return;
          ask.mutate(question);
        }}
      >
        <div className="mb-3 flex items-center gap-2">
          <span className="grid size-8 place-items-center rounded-lg bg-accent/15 text-accent">
            <Bot className="size-4" />
          </span>
          <p className="text-[13px] font-semibold">Ask the operating system</p>
        </div>
        <Textarea value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask about projects, focus, invoices, or people…" />
        <div className="mt-3 flex justify-end">
          <Button type="submit" loading={ask.isPending}>
            Ask Sunny
          </Button>
        </div>
      </form>
      <div className="mt-5 space-y-3">
        {history.map((h, i) => (
          <article key={i} className="panel p-5">
            <p className="text-[12px] font-medium text-accent">{h.q}</p>
            <p className="mt-2 whitespace-pre-line text-[14px] leading-6">{h.a}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
