"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";
import { JiraConnection } from "@/components/agents/jira-card";
import { useSession } from "@/components/layout/session";
import { Badge, Card, CardHeader, PageHeader } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { agentTheme } from "@/lib/agents";
import { cn, initials } from "@/lib/utils";

function JiraReturnToast() {
  const params = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  useEffect(() => {
    const state = params.get("jira");
    if (!state) return;
    if (state === "connected") toast("Jira connected", "success");
    else toast(`Jira connection failed: ${params.get("detail") ?? "unknown error"}`, "error");
    router.replace("/settings");
  }, [params, router, toast]);
  return null;
}

export default function SettingsPage() {
  const { me, can } = useSession();
  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-8">
      <Suspense><JiraReturnToast /></Suspense>
      <PageHeader title="Settings" description="Your profile, access and connected tools." />
      <div className="space-y-6">
        <Card>
          <CardHeader title="Profile" description="Managed by your workspace administrator." />
          <div className="flex items-center gap-4 p-5">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-900 text-lg font-semibold text-white">{initials(me.full_name || me.username)}</div>
            <div>
              <div className="text-lg font-semibold text-slate-900">{me.full_name || me.username}</div>
              <div className="text-sm text-slate-500">@{me.username}</div>
            </div>
            <Badge tone={me.role === "admin" ? "violet" : "slate"} className="ml-auto">{me.role === "admin" ? "Administrator" : "Member"}</Badge>
          </div>
        </Card>

        <Card>
          <CardHeader title="Your agents" description="Agents you can use right now." />
          <div className="grid gap-3 p-5 sm:grid-cols-2">
            {me.available_agents.length === 0 && <p className="text-sm text-slate-500">No agents enabled. Ask an administrator for access.</p>}
            {me.available_agents.map((a) => {
              const t = agentTheme(a.name);
              return (
                <div key={a.name} className="flex items-center gap-3 rounded-xl border border-slate-200 p-3">
                  <span className={cn("flex h-9 w-9 items-center justify-center rounded-lg", t.tint, t.text)}><t.icon className="h-4 w-4" /></span>
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-slate-900">{t.title}</div>
                    <div className="truncate text-xs text-slate-500">{a.summary}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        {can("pm") && (
          <Card>
            <CardHeader title="Jira" description="Lets the PM agent read your projects, sprints and velocity." />
            <div className="max-w-lg p-5"><JiraConnection /></div>
          </Card>
        )}
      </div>
    </div>
  );
}
