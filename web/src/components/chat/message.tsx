"use client";

import { AlertTriangle, Check, Copy, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { agentTheme } from "@/lib/agents";
import type { AgentName, Artifact, PartInfo, Responder } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Artifacts } from "./artifacts";
import { Markdown } from "./markdown";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: Responder | null;
  routeReason?: string | null;
  artifacts?: Artifact[];
  parts?: PartInfo[];
  error?: boolean;
  retryText?: string;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
      className="rounded-lg p-1.5 text-slate-400 opacity-0 transition hover:bg-slate-100 hover:text-slate-700 group-hover:opacity-100"
      aria-label="Copy reply"
    >
      {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

export function MessageView({ m, onRetry }: { m: ChatMessage; onRetry?: (text: string) => void }) {
  if (m.role === "user") {
    return (
      <div className="animate-in flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-brand px-4 py-2.5 text-[15px] leading-relaxed text-white">
          {m.content}
        </div>
      </div>
    );
  }
  const t = agentTheme(m.agent);
  return (
    <div className="animate-in group flex gap-3">
      <span className={cn("mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", m.error ? "bg-red-50 text-red-600" : `${t.tint} ${t.text}`)}>
        {m.error ? <AlertTriangle className="h-4 w-4" /> : <t.icon className="h-4 w-4" />}
      </span>
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-900">{m.error ? "Something went wrong" : t.title}</span>
          {m.routeReason && <span className="truncate text-xs text-slate-400" title={m.routeReason}>· {m.routeReason}</span>}
          <span className="ml-auto"><CopyButton text={m.content} /></span>
        </div>
        {m.parts && m.parts.length > 0 && (
          <div className="mb-2 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
            Combined from
            {m.parts.map((p) => {
              const pt = agentTheme(p.agent);
              return (
                <span key={p.agent} title={p.task} className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium", p.ok ? `${pt.tint} ${pt.text}` : "bg-red-50 text-red-600")}>
                  <pt.icon className="h-3 w-3" />{pt.label}{!p.ok && " (failed)"}
                </span>
              );
            })}
          </div>
        )}
        <div className={cn("rounded-2xl rounded-tl-md border bg-white px-5 py-4", m.error ? "border-red-200" : "border-slate-200")}>
          <Markdown content={m.content} />
          {m.error && m.retryText && onRetry && (
            <button onClick={() => onRetry(m.retryText!)} className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">
              <RotateCcw className="h-3.5 w-3.5" /> Try again
            </button>
          )}
        </div>
        <Artifacts items={m.artifacts ?? []} />
      </div>
    </div>
  );
}

export interface PartProgress { agent: AgentName; status: "started" | "done" | "error" }

export function ThinkingView({ agent, stage, startedAt, parts = [], synthesizing = false }: {
  agent: Responder | null; stage: "routing" | "working"; startedAt: number; parts?: PartProgress[]; synthesizing?: boolean;
}) {
  const [now, setNow] = useState(startedAt);
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const t = agentTheme(stage === "routing" ? "supervisor" : agent);
  const elapsed = Math.max(0, Math.floor((now - startedAt) / 1000));
  const label = stage === "routing" ? "Finding the right agent"
    : agent === "multi" ? (synthesizing ? "Combining the results" : `Coordinating ${parts.length || "several"} agents`)
    : `${t.title} is working on it`;
  return (
    <div className="animate-in flex gap-3">
      <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", t.tint, t.text)}>
        <t.icon className="h-4 w-4" />
      </span>
      <div className="flex flex-wrap items-center gap-3 rounded-2xl rounded-tl-md border border-slate-200 bg-white px-4 py-3">
        <span className="flex gap-1">
          <span className="typing-dot h-1.5 w-1.5 rounded-full bg-slate-400" />
          <span className="typing-dot h-1.5 w-1.5 rounded-full bg-slate-400" />
          <span className="typing-dot h-1.5 w-1.5 rounded-full bg-slate-400" />
        </span>
        <span className="text-sm text-slate-600">{label}…</span>
        <span className="text-xs tabular-nums text-slate-400">{elapsed}s</span>
        {parts.length > 0 && (
          <span className="flex flex-wrap gap-1.5 border-l border-slate-200 pl-3">
            {parts.map((p) => {
              const pt = agentTheme(p.agent);
              return (
                <span key={p.agent} className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                  p.status === "done" ? `${pt.tint} ${pt.text}` : p.status === "error" ? "bg-red-50 text-red-600" : "bg-slate-100 text-slate-500")}>
                  <pt.icon className="h-3 w-3" />{pt.label}{p.status === "done" ? " ✓" : p.status === "error" ? " ✕" : "…"}
                </span>
              );
            })}
          </span>
        )}
      </div>
    </div>
  );
}
