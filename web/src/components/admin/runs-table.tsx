"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge, Drawer, EmptyState } from "@/components/ui/primitives";
import { agentTheme } from "@/lib/agents";
import type { AgentRunRow } from "@/lib/types";
import { cn, formatDateTime, seconds } from "@/lib/utils";

const STATUS_TONE = { ok: "green", error: "red", refused: "amber" } as const;

export function RunsTable({ runs, showUser }: { runs: AgentRunRow[]; showUser?: boolean }) {
  const [selected, setSelected] = useState<AgentRunRow | null>(null);
  if (runs.length === 0) return <EmptyState title="No activity yet" description="Runs appear here as soon as someone chats with an agent." />;
  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-100 bg-slate-50/60 text-slate-500">
            <tr>
              <th className="px-5 py-3 font-medium">Time</th>
              {showUser && <th className="px-5 py-3 font-medium">User</th>}
              <th className="px-5 py-3 font-medium">Agent</th>
              <th className="px-5 py-3 font-medium">Request</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 text-right font-medium">Latency</th>
              <th className="px-5 py-3 text-right font-medium">Tools</th>
              <th className="px-5 py-3 text-right font-medium">Tokens</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {runs.map((r) => {
              const t = agentTheme(r.agent);
              return (
                <tr key={r.id} onClick={() => setSelected(r)} className="cursor-pointer hover:bg-slate-50/70">
                  <td className="whitespace-nowrap px-5 py-3 text-slate-500">{formatDateTime(r.created_at)}</td>
                  {showUser && <td className="px-5 py-3 text-slate-700">@{r.user}</td>}
                  <td className="px-5 py-3">
                    <span className={cn("inline-flex items-center gap-1.5 font-medium", t.text)}><t.icon className="h-3.5 w-3.5" />{t.label}</span>
                  </td>
                  <td className="max-w-[340px] truncate px-5 py-3 text-slate-700">{r.message}</td>
                  <td className="px-5 py-3"><Badge tone={STATUS_TONE[r.status]}>{r.status}</Badge></td>
                  <td className="px-5 py-3 text-right tabular-nums text-slate-600">{seconds(r.latency_ms)}</td>
                  <td className="px-5 py-3 text-right tabular-nums text-slate-600">{r.tool_calls}</td>
                  <td className="px-5 py-3 text-right tabular-nums text-slate-600">{r.tokens.toLocaleString()}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <Drawer open={!!selected} onClose={() => setSelected(null)} title={selected ? `Run #${selected.id}` : ""}>
        {selected && (
          <div className="space-y-5 text-sm">
            <div className="grid grid-cols-2 gap-3">
              {[
                ["Agent", agentTheme(selected.agent).title],
                ["Status", selected.status],
                ["User", `@${selected.user}`],
                ["When", formatDateTime(selected.created_at)],
                ["Latency", seconds(selected.latency_ms)],
                ["LLM calls", String(selected.llm_calls)],
                ["Tool calls", String(selected.tool_calls)],
                ["Tokens", selected.tokens.toLocaleString()],
              ].map(([k, v]) => (
                <div key={k} className="rounded-xl bg-slate-50 px-3 py-2">
                  <div className="text-xs text-slate-500">{k}</div>
                  <div className="font-medium capitalize text-slate-900">{v}</div>
                </div>
              ))}
            </div>
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">Request</h4>
              <p className="whitespace-pre-wrap rounded-xl border border-slate-200 p-3 text-slate-700">{selected.message}</p>
            </div>
            {selected.route_reason && (
              <div>
                <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">Routing decision</h4>
                <p className="text-slate-600">{selected.route_reason}</p>
              </div>
            )}
            {selected.error && <p className="rounded-xl bg-red-50 p-3 text-red-700">{selected.error}</p>}
            <div>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Agent steps</h4>
              {selected.trace.length === 0 ? <p className="text-slate-500">No tool steps for this run.</p> : (
                <ol className="relative space-y-3 border-l border-slate-200 pl-5">
                  {selected.trace.map((s, i) => (
                    <li key={i} className="relative">
                      <span className={cn("absolute -left-[27px] top-1 flex h-3.5 w-3.5 items-center justify-center rounded-full border-2 border-white", s.action === "final_answer" ? "bg-emerald-500" : "bg-slate-400")} />
                      <div className="font-mono text-[13px] font-medium text-slate-900">{s.action}</div>
                      {s.thought && <p className="mt-0.5 text-slate-500">{s.thought}</p>}
                      {s.args && Object.keys(s.args).length > 0 && (
                        <pre className="mt-1.5 overflow-x-auto rounded-lg bg-slate-900 p-2.5 text-xs text-slate-100">{JSON.stringify(s.args, null, 2)}</pre>
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </div>
            <Link href={`/chat/${selected.thread_id}`} className="inline-block text-sm font-medium text-blue-600 hover:underline">Open conversation →</Link>
          </div>
        )}
      </Drawer>
    </>
  );
}
