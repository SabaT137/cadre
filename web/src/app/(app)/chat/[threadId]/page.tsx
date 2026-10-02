"use client";

import { PanelRightClose, PanelRightOpen, Plus } from "lucide-react";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { mutate as globalMutate } from "swr";
import { ContextPanel } from "@/components/chat/context-panel";
import { Composer } from "@/components/chat/composer";
import { MessageView, ThinkingView, type ChatMessage } from "@/components/chat/message";
import { useStartChat } from "@/components/chat/use-start-chat";
import { useSession } from "@/components/layout/session";
import { Button, Spinner } from "@/components/ui/primitives";
import { api, ApiError } from "@/lib/api";
import { agentTheme } from "@/lib/agents";
import { streamChat } from "@/lib/stream";
import type { AgentName, Department, Responder, ThreadHistory } from "@/lib/types";
import { cn, takePendingPrompt } from "@/lib/utils";

const isAgent = (a?: string | null): a is AgentName => !!a && a !== "supervisor";

export default function ChatPage() {
  const { threadId } = useParams<{ threadId: string }>();
  const { can } = useSession();
  const startChat = useStartChat();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [pending, setPending] = useState<{ stage: "routing" | "working"; agent: Responder | null; startedAt: number } | null>(null);
  const [department, setDepartment] = useState<Department>("auto");
  const [templateId, setTemplateId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [panelOpen, setPanelOpen] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const initRef = useRef<string | null>(null);

  const send = useCallback(async (text: string, dept: Department) => {
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: text };
    setMessages((m) => [...m, userMsg]);
    setPending({ stage: dept === "auto" ? "routing" : "working", agent: dept === "auto" ? null : dept, startedAt: Date.now() });
    let routeReason: string | null = null;
    let gotMessage = false;
    try {
      for await (const ev of streamChat({ message: text, thread_id: threadId, department: dept, template_id: templateId })) {
        if (ev.event === "route") {
          routeReason = ev.data.reason;
          setPending((p) => p && { ...p, stage: "working", agent: ev.data.agent });
        } else if (ev.event === "message") {
          gotMessage = true;
          setMessages((m) => [...m, {
            id: crypto.randomUUID(), role: "assistant", content: ev.data.content,
            agent: ev.data.agent, routeReason, artifacts: ev.data.artifacts,
          }]);
        } else if (ev.event === "error") {
          throw new ApiError(502, ev.data.detail);
        }
      }
      if (!gotMessage) throw new ApiError(502, "The agent didn't return a reply.");
    } catch (e) {
      const detail = e instanceof ApiError ? e.message : "Connection lost while waiting for the agent.";
      setMessages((m) => [...m, {
        id: crypto.randomUUID(), role: "assistant", content: `${detail}\n\nPlease try again in a moment.`, error: true, retryText: text,
      }]);
    } finally {
      setPending(null);
      globalMutate((key) => typeof key === "string" && (key.startsWith("/threads") || key.startsWith("/documents") || key.startsWith("/invoices")));
    }
  }, [threadId, templateId]);

  // Load history once per thread, then send any prompt handed over from Home / Agents.
  useEffect(() => {
    if (initRef.current === threadId) return;
    initRef.current = threadId;
    const pendingPrompt = takePendingPrompt(threadId);
    setMessages([]);
    setLoaded(false);
    (async () => {
      try {
        // A hand-over from Home/Agents means this thread was just created client-side: no history yet.
        if (pendingPrompt) return;
        const h = await api<ThreadHistory>(`/threads/${threadId}`);
        setMessages(h.messages.map((m, i) => ({
          id: `h${i}`, role: m.role, content: m.content, agent: m.agent ?? null, artifacts: m.artifacts,
        })));
      } catch (e) {
        if (!(e instanceof ApiError && e.status === 404)) console.error(e);
      } finally {
        setLoaded(true);
      }
      if (pendingPrompt) {
        const dept = (pendingPrompt.department as Department) || "auto";
        setDepartment(dept);
        if (pendingPrompt.message) send(pendingPrompt.message, dept);
      }
    })();
  }, [threadId, send]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, pending]);

  const lastAgent = [...messages].reverse().find((m) => m.role === "assistant" && isAgent(m.agent))?.agent as AgentName | undefined;
  const focusAgent: AgentName | null = department !== "auto" ? department : pending && isAgent(pending.agent) ? pending.agent : lastAgent ?? null;
  const title = messages.find((m) => m.role === "user")?.content ?? "New conversation";
  const empty = loaded && messages.length === 0 && !pending;
  const focusTheme = agentTheme(focusAgent);

  return (
    <div className="flex h-full">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
          <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", focusTheme.tint, focusTheme.text)}>
            <focusTheme.icon className="h-4 w-4" />
          </span>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-[15px] font-semibold text-slate-900">{title}</h1>
            <p className="text-xs text-slate-500">{focusAgent ? `With ${focusTheme.title}` : "The orchestrator routes each message"}</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => startChat("", "auto")}><Plus className="h-4 w-4" /> New chat</Button>
          <button onClick={() => setPanelOpen((o) => !o)} className="hidden rounded-lg p-2 text-slate-500 hover:bg-slate-100 xl:block" aria-label="Toggle panel">
            {panelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
          </button>
        </div>

        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6">
            {!loaded && <div className="flex justify-center py-20"><Spinner /></div>}
            {empty && (
              <div className="py-16 text-center">
                <span className={cn("mx-auto flex h-14 w-14 items-center justify-center rounded-2xl", focusTheme.tint, focusTheme.text)}>
                  <focusTheme.icon className="h-6 w-6" />
                </span>
                <h2 className="mt-4 text-xl font-semibold text-slate-900">{focusAgent ? `Start a conversation with ${focusTheme.title}` : "What can we help with?"}</h2>
                <p className="mt-1 text-sm text-slate-500">{focusAgent ? focusTheme.capabilities.join(" · ") : "Describe your task and the orchestrator will pick the right agent."}</p>
                {focusAgent && (
                  <div className="mx-auto mt-6 flex max-w-xl flex-col gap-2">
                    {focusTheme.examples.map((ex) => (
                      <button key={ex} onClick={() => setDraft(ex)} className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-left text-sm text-slate-600 shadow-sm hover:border-slate-300 hover:text-slate-900">
                        {ex}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            {messages.map((m) => <MessageView key={m.id} m={m} onRetry={(t) => send(t, department)} />)}
            {pending && <ThinkingView agent={pending.agent} stage={pending.stage} startedAt={pending.startedAt} />}
          </div>
        </div>

        <div className="border-t border-slate-200 bg-slate-50/80 px-4 py-4 backdrop-blur sm:px-6">
          <div className="mx-auto max-w-3xl">
            <Composer
              variant="dock"
              value={draft}
              onValueChange={setDraft}
              department={department}
              onDepartmentChange={setDepartment}
              disabled={!!pending}
              onSubmit={(text) => send(text, department)}
              placeholder={focusAgent ? `Message ${focusTheme.title}…` : "Ask anything or describe a task…"}
            />
            <p className="mt-2 text-center text-[11px] text-slate-400">Agents can make mistakes. Review contracts, invoices and plans before sending them.</p>
          </div>
        </div>
      </div>

      {panelOpen && (
        <aside className="hidden w-[320px] shrink-0 overflow-y-auto border-l border-slate-200 bg-slate-50 p-4 xl:block">
          <ContextPanel
            agent={focusAgent && can(focusAgent) ? focusAgent : null}
            templateId={templateId}
            onTemplate={setTemplateId}
            onExample={setDraft}
          />
        </aside>
      )}
    </div>
  );
}
