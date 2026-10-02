"use client";

import useSWR from "swr";
import { AdminGuard } from "@/components/admin/admin-guard";
import { useSession } from "@/components/layout/session";
import { Badge, Card, PageHeader, Skeleton, Toggle } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, fetcher } from "@/lib/api";
import { agentTheme } from "@/lib/agents";
import type { AdminAgent } from "@/lib/types";
import { cn, seconds } from "@/lib/utils";

function Agents() {
  const toast = useToast();
  const { refresh } = useSession();
  const { data, mutate } = useSWR<AdminAgent[]>("/admin/agents", fetcher);

  async function toggle(a: AdminAgent, enabled: boolean) {
    mutate(data?.map((x) => (x.name === a.name ? { ...x, enabled } : x)), false);
    try {
      await api(`/admin/agents/${a.name}`, { method: "PATCH", json: { enabled } });
      toast(`${agentTheme(a.name).title} ${enabled ? "enabled" : "disabled"}`, "success");
      refresh();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Update failed", "error");
    } finally {
      mutate();
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-8">
      <PageHeader title="Agents & access" description="Switch agents on or off for the whole workspace. Per-user access is set on the Users page." />
      {!data ? <div className="grid gap-4 md:grid-cols-2">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-44" />)}</div> : (
        <div className="grid gap-4 md:grid-cols-2">
          {data.map((a) => {
            const t = agentTheme(a.name);
            const isSupervisor = a.name === "supervisor";
            return (
              <Card key={a.name} className={cn("overflow-hidden", !a.enabled && "opacity-70")}>
                <div className={cn("h-1.5", t.accent)} />
                <div className="p-5">
                  <div className="flex items-start gap-3">
                    <span className={cn("flex h-11 w-11 items-center justify-center rounded-xl", t.tint, t.text)}><t.icon className="h-5 w-5" /></span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-slate-900">{t.title}</h3>
                        {a.enabled ? <Badge tone="green">Enabled</Badge> : <Badge>Disabled</Badge>}
                      </div>
                      <p className="mt-0.5 text-sm text-slate-500">{a.summary}</p>
                    </div>
                    {isSupervisor ? <span className="text-xs text-slate-400">Always on</span> : <Toggle checked={a.enabled} onChange={(v) => toggle(a, v)} label={`Enable ${a.label}`} />}
                  </div>
                  <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
                    <div className="rounded-xl bg-slate-50 px-3 py-2"><div className="text-xs text-slate-500">Runs (7d)</div><div className="font-semibold text-slate-900">{a.runs_7d}</div></div>
                    <div className="rounded-xl bg-slate-50 px-3 py-2"><div className="text-xs text-slate-500">Errors (7d)</div><div className={cn("font-semibold", a.errors_7d ? "text-red-600" : "text-slate-900")}>{a.errors_7d}</div></div>
                    <div className="rounded-xl bg-slate-50 px-3 py-2"><div className="text-xs text-slate-500">Avg latency</div><div className="font-semibold text-slate-900">{seconds(a.avg_latency_ms)}</div></div>
                  </div>
                  <div className="mt-4 text-xs text-slate-500">
                    Model <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-slate-700">{a.model}</code>
                  </div>
                  {a.tools.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {a.tools.map((tool) => <span key={tool} className="rounded-md border border-slate-200 bg-white px-1.5 py-0.5 font-mono text-[11px] text-slate-600">{tool}</span>)}
                    </div>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function AdminAgentsPage() {
  return <AdminGuard><Agents /></AdminGuard>;
}
