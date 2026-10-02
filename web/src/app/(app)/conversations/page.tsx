"use client";

import { MessagesSquare, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import useSWR from "swr";
import { useStartChat } from "@/components/chat/use-start-chat";
import { Button, Card, EmptyState, Input, PageHeader, Skeleton } from "@/components/ui/primitives";
import { fetcher } from "@/lib/api";
import { AGENT_ORDER, agentTheme } from "@/lib/agents";
import type { ThreadSummary } from "@/lib/types";
import { cn, formatDateTime, timeAgo } from "@/lib/utils";

function Conversations() {
  const params = useSearchParams();
  const start = useStartChat();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [agent, setAgent] = useState<string>("all");
  const { data } = useSWR<ThreadSummary[]>("/threads?limit=200", fetcher);

  const filtered = useMemo(() => (data ?? []).filter((t) =>
    (agent === "all" || t.agent === agent) && (!q.trim() || t.title.toLowerCase().includes(q.trim().toLowerCase())),
  ), [data, q, agent]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-8">
      <PageHeader
        title="My Conversations"
        description="Every conversation you've had with your agents."
        action={<Button onClick={() => start("", "auto")}><Plus className="h-4 w-4" /> New conversation</Button>}
      />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-[240px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by title…" className="pl-9" />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {["all", ...AGENT_ORDER].map((a) => (
            <button
              key={a}
              onClick={() => setAgent(a)}
              className={cn("rounded-full border px-3 py-1.5 text-sm", agent === a ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 bg-white text-slate-600 hover:text-slate-900")}
            >
              {a === "all" ? "All" : agentTheme(a).label}
            </button>
          ))}
        </div>
      </div>
      <Card>
        {!data ? (
          <div className="space-y-3 p-5">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-12" />)}</div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={<MessagesSquare className="h-5 w-5" />} title={data.length ? "No matches" : "No conversations yet"} description={data.length ? "Try a different search or filter." : "Start one from Home or the button above."} />
        ) : (
          <ul className="divide-y divide-slate-100">
            {filtered.map((t) => {
              const theme = agentTheme(t.agent);
              return (
                <li key={t.thread_id}>
                  <Link href={`/chat/${t.thread_id}`} className="flex items-center gap-4 px-5 py-4 hover:bg-slate-50">
                    <span className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl", theme.tint, theme.text)}>
                      <theme.icon className="h-[18px] w-[18px]" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium text-slate-900">{t.title || "Untitled"}</span>
                      <span className="text-sm text-slate-500">{t.agent ? theme.title : "Orchestrator"} · {t.turns} message{t.turns === 1 ? "" : "s"}</span>
                    </span>
                    <span className="hidden text-right text-sm text-slate-500 sm:block" title={formatDateTime(t.updated_at)}>{timeAgo(t.updated_at)}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </div>
  );
}

export default function ConversationsPage() {
  return <Suspense><Conversations /></Suspense>;
}
