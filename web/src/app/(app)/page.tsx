"use client";

import { ArrowRight, FileText, MessagesSquare } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";
import { AgentCard } from "@/components/agents/agent-card";
import { Composer } from "@/components/chat/composer";
import { useStartChat } from "@/components/chat/use-start-chat";
import { useSession } from "@/components/layout/session";
import { Card, EmptyState } from "@/components/ui/primitives";
import { fetcher, fileUrl } from "@/lib/api";
import { AGENT_ORDER, HOME_SUGGESTIONS, agentTheme } from "@/lib/agents";
import type { Department, DocumentInfo, ThreadSummary } from "@/lib/types";
import { cn, firstName, greeting, timeAgo } from "@/lib/utils";

export default function HomePage() {
  const { me, can } = useSession();
  const start = useStartChat();
  const [department, setDepartment] = useState<Department>("auto");
  const [draft, setDraft] = useState("");
  const { data: threads } = useSWR<ThreadSummary[]>("/threads?limit=5", fetcher);
  const { data: docs } = useSWR<DocumentInfo[]>("/documents?limit=5", fetcher);

  const agents = AGENT_ORDER.filter(can);
  const suggestions = HOME_SUGGESTIONS.filter((s) => can(s.agent)).slice(0, 4);

  return (
    <div className="mx-auto max-w-[1280px] px-4 pb-16 pt-12 sm:px-8 sm:pt-14">
      <div className="text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-[40px] sm:leading-[1.15]">
          {greeting()}, {firstName(me.full_name || me.username)}.
        </h1>
        <p className="mt-1 text-3xl font-semibold tracking-tight text-[#4b6580] sm:text-[40px] sm:leading-[1.15]">
          How can your AI team help today?
        </p>
      </div>

      <div className="mx-auto mt-9 max-w-[864px]">
        {agents.length === 0 ? (
          <Card><EmptyState title="No assistants yet" description="Your administrator hasn't given you access to any agents. Ask them to enable one for you." /></Card>
        ) : (
          <>
            <Composer
              autoFocus
              value={draft}
              onValueChange={setDraft}
              department={department}
              onDepartmentChange={setDepartment}
              onSubmit={(text) => start(text, department)}
            />
            <div className="mt-5 flex flex-wrap justify-center gap-2.5">
              {suggestions.map((s) => (
                <button
                  key={s.text}
                  onClick={() => { setDraft(s.text); setDepartment(s.agent); }}
                  className="rounded-full border border-slate-200 bg-white px-4 py-2 text-[13px] text-slate-600 shadow-sm transition hover:border-slate-300 hover:text-slate-900"
                >
                  {s.text}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {agents.length > 0 && (
        <div className={cn(
          "mx-auto mt-14 grid gap-5 sm:grid-cols-2",
          agents.length >= 5 ? "xl:grid-cols-5" : agents.length === 4 ? "xl:grid-cols-4" : "lg:grid-cols-3",
        )}>
          {agents.map((a) => <AgentCard key={a} name={a} onStart={() => start("", a)} />)}
        </div>
      )}

      <div className="mt-12 grid gap-5 lg:grid-cols-2">
        <Card>
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <h3 className="font-semibold text-slate-900">Recent conversations</h3>
            <Link href="/conversations" className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900">View all <ArrowRight className="h-3.5 w-3.5" /></Link>
          </div>
          {threads && threads.length === 0 && <EmptyState icon={<MessagesSquare className="h-5 w-5" />} title="No conversations yet" description="Ask anything above to get started." />}
          <ul className="divide-y divide-slate-100">
            {threads?.map((t) => {
              const theme = agentTheme(t.agent);
              return (
                <li key={t.thread_id}>
                  <Link href={`/chat/${t.thread_id}`} className="flex items-center gap-3 px-5 py-3 hover:bg-slate-50">
                    <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", theme.tint, theme.text)}>
                      <theme.icon className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-slate-800">{t.title || "Untitled"}</span>
                      <span className="text-xs text-slate-500">{t.agent ? theme.title : "Orchestrator"} · {timeAgo(t.updated_at)}</span>
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </Card>
        <Card>
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <h3 className="font-semibold text-slate-900">Recent documents</h3>
            <Link href="/documents" className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900">View all <ArrowRight className="h-3.5 w-3.5" /></Link>
          </div>
          {docs && docs.length === 0 && <EmptyState icon={<FileText className="h-5 w-5" />} title="No documents yet" description="Contracts, invoices and plans your agents create will appear here." />}
          <ul className="divide-y divide-slate-100">
            {docs?.map((d) => {
              const theme = agentTheme(d.agent);
              return (
                <li key={d.file_id} className="flex items-center gap-3 px-5 py-3">
                  <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", theme.tint, theme.text)}>
                    <FileText className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-slate-800">{d.filename}</span>
                    <span className="text-xs capitalize text-slate-500">{d.kind} · {timeAgo(d.created_at)}</span>
                  </span>
                  <a href={fileUrl(d.file_id)} className="text-sm font-medium text-slate-600 hover:text-slate-900">Download</a>
                </li>
              );
            })}
          </ul>
        </Card>
      </div>
    </div>
  );
}
