"use client";

import { ArrowRight } from "lucide-react";
import { agentTheme } from "@/lib/agents";
import type { AgentName } from "@/lib/types";
import { cn } from "@/lib/utils";

export function AgentCard({ name, onStart, available = true, detail = false, onExample }: {
  name: AgentName;
  onStart: () => void;
  available?: boolean;
  detail?: boolean;
  onExample?: (prompt: string) => void;
}) {
  const t = agentTheme(name);
  return (
    <div className="group relative flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(15,23,42,0.08)]">
      <div className={cn("h-1.5 w-full", t.accent)} />
      <div className="flex flex-1 flex-col p-5">
        <div className="flex items-start justify-between">
          <span className={cn("flex h-11 w-11 items-center justify-center rounded-xl", t.tint, t.text)}>
            <t.icon className="h-5 w-5" />
          </span>
          {available ? (
            <span className="flex items-center gap-1.5 text-[13px] text-emerald-600">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Available
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-[13px] text-slate-400">
              <span className="h-1.5 w-1.5 rounded-full bg-slate-300" /> Unavailable
            </span>
          )}
        </div>
        <h3 className="mt-4 text-lg font-semibold text-slate-900">{t.title}</h3>
        <ul className="mt-2 space-y-1.5 text-[15px] text-slate-500">
          {t.capabilities.map((c) => <li key={c}>{c}</li>)}
        </ul>
        {detail && onExample && (
          <div className="mt-4 space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Try</p>
            {t.examples.map((ex) => (
              <button
                key={ex}
                onClick={() => onExample(ex)}
                className="block w-full rounded-xl border border-slate-200 bg-slate-50/60 px-3 py-2 text-left text-[13px] text-slate-600 hover:border-slate-300 hover:bg-white"
              >
                “{ex}”
              </button>
            ))}
          </div>
        )}
        <div className="flex-1" />
        <button
          onClick={onStart}
          disabled={!available}
          className="mt-5 flex h-10 w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white text-sm font-medium text-slate-900 shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
        >
          Start conversation <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
        </button>
      </div>
    </div>
  );
}
