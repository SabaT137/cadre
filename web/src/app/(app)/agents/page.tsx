"use client";

import { Sparkles } from "lucide-react";
import { AgentCard } from "@/components/agents/agent-card";
import { useStartChat } from "@/components/chat/use-start-chat";
import { useSession } from "@/components/layout/session";
import { Card, PageHeader } from "@/components/ui/primitives";
import { AGENT_ORDER } from "@/lib/agents";

export default function AgentsPage() {
  const { can, isAdmin } = useSession();
  const start = useStartChat();
  const mine = AGENT_ORDER.filter(can);
  const others = AGENT_ORDER.filter((a) => !can(a));

  return (
    <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-8">
      <PageHeader title="AI Agents" description="Specialist agents you can work with. The orchestrator routes requests automatically, or pick one directly." />

      <Card className="mb-8 flex items-start gap-4 p-5">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-white"><Sparkles className="h-5 w-5" /></span>
        <div>
          <h3 className="font-semibold text-slate-900">Orchestrator</h3>
          <p className="mt-1 text-sm text-slate-500">
            Every message first goes to the orchestrator. It reads your request and hands it to the right specialist. Follow-up questions stay with the same agent until you change topic. You can also choose an agent directly from the composer.
          </p>
        </div>
      </Card>

      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {mine.map((a) => (
          <AgentCard key={a} name={a} detail onStart={() => start("", a)} onExample={(p) => start(p, a)} />
        ))}
      </div>

      {others.length > 0 && (
        <>
          <h2 className="mb-4 mt-12 text-sm font-semibold uppercase tracking-wider text-slate-400">Not enabled for you</h2>
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {others.map((a) => <AgentCard key={a} name={a} available={false} onStart={() => {}} />)}
          </div>
          <p className="mt-4 text-sm text-slate-500">{isAdmin ? "These agents are switched off in Admin → Agents & access." : "Ask your administrator if you need access to these agents."}</p>
        </>
      )}
    </div>
  );
}
