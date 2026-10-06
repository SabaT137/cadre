"use client";

import { Activity, AlertTriangle, Clock, Coins, MessagesSquare, Users } from "lucide-react";
import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import useSWR from "swr";
import { AdminGuard } from "@/components/admin/admin-guard";
import { RunsTable } from "@/components/admin/runs-table";
import { Card, CardHeader, PageHeader, Select, Skeleton, Tabs } from "@/components/ui/primitives";
import { fetcher } from "@/lib/api";
import { AGENT_ORDER, agentTheme } from "@/lib/agents";
import type { AdminStats, AdminUser, AgentRunRow } from "@/lib/types";
import { seconds } from "@/lib/utils";

const CHART_COLORS: Record<string, string> = {
  hr: "#8b5cf6", devops: "#3b82f6", finance: "#f97316", pm: "#14b8a6", developer: "#10b981", supervisor: "#1c344a", multi: "#00a2ad", unknown: "#cbd5e1",
};

function Kpi({ icon: Icon, label, value, hint }: { icon: typeof Activity; label: string; value: string; hint?: string }) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-500">{label}</span>
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-600"><Icon className="h-4 w-4" /></span>
      </div>
      <div className="mt-3 text-2xl font-semibold tracking-tight text-slate-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </Card>
  );
}

function Overview() {
  const [days, setDays] = useState(7);
  const [filters, setFilters] = useState({ agent: "", user: "", status: "" });
  const { data: s } = useSWR<AdminStats>(`/admin/stats?days=${days}`, fetcher, { refreshInterval: 30_000 });
  const qs = new URLSearchParams({ ...filters, limit: "100" }).toString();
  const { data: runs } = useSWR<AgentRunRow[]>(`/admin/runs?${qs}`, fetcher, { refreshInterval: 30_000 });
  const { data: users } = useSWR<AdminUser[]>("/admin/users", fetcher);

  const perDay = useMemo(() => {
    if (!s) return [];
    const byDate: Record<string, Record<string, number | string>> = {};
    for (const r of s.per_day) {
      byDate[r.date] ??= { date: r.date.slice(5) };
      byDate[r.date][r.agent] = r.runs;
    }
    return Object.values(byDate);
  }, [s]);
  const agentsInData = useMemo(() => (s ? Object.keys(s.per_agent) : []), [s]);
  const perAgent = useMemo(() => (s ? Object.entries(s.per_agent).map(([agent, v]) => ({
    agent, label: agentTheme(agent).label, ...v, latency_s: +(v.avg_latency_ms / 1000).toFixed(1),
  })) : []), [s]);

  return (
    <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-8">
      <PageHeader
        title="Workspace overview"
        description="Usage, performance and activity across all agents."
        action={<Tabs value={String(days)} onChange={(v) => setDays(Number(v))} items={[1, 7, 30, 90].map((d) => ({ value: String(d), label: d === 1 ? "24h" : `${d}d` }))} />}
      />
      {!s ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-28" />)}</div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <Kpi icon={MessagesSquare} label="Requests" value={s.requests.toLocaleString()} hint={`${s.requests_today} today`} />
            <Kpi icon={Users} label="Active users" value={`${s.active_users}`} hint={`of ${s.users_total} accounts`} />
            <Kpi icon={AlertTriangle} label="Error rate" value={`${s.error_rate}%`} hint={`${s.refused} refused (no access)`} />
            <Kpi icon={Clock} label="Avg latency" value={seconds(s.avg_latency_ms)} hint={`p95 ${seconds(s.p95_latency_ms)}`} />
            <Kpi icon={Coins} label="Tokens" value={s.tokens.toLocaleString()} hint="prompt + completion" />
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title="Requests per day" description="Stacked by agent" />
              <div className="h-72 p-4">
                {perDay.length === 0 ? <p className="py-24 text-center text-sm text-slate-400">No requests in this period.</p> : (
                  <ResponsiveContainer>
                    <BarChart data={perDay}>
                      <CartesianGrid vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="date" tickLine={false} axisLine={false} fontSize={12} stroke="#94a3b8" />
                      <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={12} stroke="#94a3b8" width={30} />
                      <Tooltip cursor={{ fill: "#f8fafc" }} contentStyle={{ borderRadius: 12, borderColor: "#e2e8f0", fontSize: 13 }} />
                      <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} formatter={(v) => agentTheme(String(v)).label} />
                      {agentsInData.map((a, i) => (
                        <Bar key={a} dataKey={a} stackId="a" fill={CHART_COLORS[a] ?? "#94a3b8"} radius={i === agentsInData.length - 1 ? [6, 6, 0, 0] : 0} />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </Card>
            <Card>
              <CardHeader title="Routing share" description="Which agents handle requests" />
              <div className="h-72 p-4">
                {perAgent.length === 0 ? <p className="py-24 text-center text-sm text-slate-400">No data.</p> : (
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie data={perAgent} dataKey="runs" nameKey="label" innerRadius={60} outerRadius={95} paddingAngle={2}>
                        {perAgent.map((p) => <Cell key={p.agent} fill={CHART_COLORS[p.agent] ?? "#94a3b8"} />)}
                      </Pie>
                      <Tooltip contentStyle={{ borderRadius: 12, borderColor: "#e2e8f0", fontSize: 13 }} />
                      <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
            </Card>
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader title="Average latency by agent" description="Seconds per request" />
              <div className="h-64 p-4">
                <ResponsiveContainer>
                  <BarChart data={perAgent} layout="vertical" margin={{ left: 10 }}>
                    <CartesianGrid horizontal={false} stroke="#f1f5f9" />
                    <XAxis type="number" tickLine={false} axisLine={false} fontSize={12} stroke="#94a3b8" />
                    <YAxis type="category" dataKey="label" tickLine={false} axisLine={false} fontSize={12} stroke="#64748b" width={90} />
                    <Tooltip cursor={{ fill: "#f8fafc" }} contentStyle={{ borderRadius: 12, borderColor: "#e2e8f0", fontSize: 13 }} formatter={(v) => [`${v}s`, "Avg latency"]} />
                    <Bar dataKey="latency_s" radius={[0, 6, 6, 0]}>
                      {perAgent.map((p) => <Cell key={p.agent} fill={CHART_COLORS[p.agent] ?? "#94a3b8"} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card>
              <CardHeader title="Top users" description="Requests in this period" />
              <ul className="divide-y divide-slate-100">
                {s.per_user.length === 0 && <li className="px-5 py-8 text-center text-sm text-slate-400">No users yet.</li>}
                {s.per_user.slice(0, 8).map((u) => {
                  const pct = Math.round((u.runs / Math.max(1, s.requests)) * 100);
                  return (
                    <li key={u.user} className="px-5 py-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-slate-800">@{u.user}</span>
                        <span className="tabular-nums text-slate-500">{u.runs} · {pct}%</span>
                      </div>
                      <div className="mt-1.5 h-1.5 rounded-full bg-slate-100"><div className="h-1.5 rounded-full bg-brand" style={{ width: `${pct}%` }} /></div>
                    </li>
                  );
                })}
              </ul>
            </Card>
          </div>
        </>
      )}

      <Card className="mt-6">
        <CardHeader
          title="Activity log"
          description="Click a run to see the routing decision and every step the agent took."
          action={
            <div className="flex flex-wrap gap-2">
              <Select value={filters.agent} onChange={(e) => setFilters((f) => ({ ...f, agent: e.target.value }))} className="h-9 w-36">
                <option value="">All agents</option>
                {[...AGENT_ORDER, "supervisor"].map((a) => <option key={a} value={a}>{agentTheme(a).label}</option>)}
              </Select>
              <Select value={filters.user} onChange={(e) => setFilters((f) => ({ ...f, user: e.target.value }))} className="h-9 w-36">
                <option value="">All users</option>
                {users?.map((u) => <option key={u.id} value={u.username}>@{u.username}</option>)}
              </Select>
              <Select value={filters.status} onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))} className="h-9 w-32">
                <option value="">All statuses</option>
                <option value="ok">OK</option>
                <option value="error">Error</option>
                <option value="refused">Refused</option>
              </Select>
            </div>
          }
        />
        {!runs ? <div className="p-5"><Skeleton className="h-40" /></div> : <RunsTable runs={runs} showUser />}
      </Card>
    </div>
  );
}

export default function AdminOverviewPage() {
  return <AdminGuard><Overview /></AdminGuard>;
}
