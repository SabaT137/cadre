"use client";

import { LogOut, Menu, MessagesSquare, Search, Settings } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import useSWR from "swr";
import { fetcher, logout } from "@/lib/api";
import { agentTheme } from "@/lib/agents";
import type { Health, ThreadSummary } from "@/lib/types";
import { cn, initials, timeAgo } from "@/lib/utils";
import { useSession } from "./session";

function SystemStatus() {
  const { data, error } = useSWR<Health>("/health", fetcher, { refreshInterval: 60_000 });
  const ok = !!data && data.status === "ok" && !error;
  return (
    <div
      className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 md:flex"
      title={data ? `Orchestrator: ${data.supervisor_model} · Agents: ${data.worker_model}` : undefined}
    >
      <span className={cn("h-2 w-2 rounded-full", ok ? "bg-emerald-500" : data || error ? "bg-red-500" : "bg-slate-300")} />
      {ok ? "All systems operational" : error ? "Service unavailable" : "Checking…"}
    </div>
  );
}

function GlobalSearch() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { data: threads } = useSWR<ThreadSummary[]>(open ? "/threads?limit=200" : null, fetcher);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const results = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term || !threads) return [];
    return threads.filter((t) => t.title.toLowerCase().includes(term)).slice(0, 6);
  }, [q, threads]);

  return (
    <div className="relative w-full max-w-xl">
      <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
      <input
        ref={inputRef}
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && q.trim()) {
            router.push(`/conversations?q=${encodeURIComponent(q.trim())}`);
            setOpen(false);
          }
        }}
        placeholder="Search conversations, documents…"
        className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-14 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-300 focus:outline-none focus:ring-4 focus:ring-slate-100"
      />
      <kbd className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded-md border border-slate-200 px-1.5 py-0.5 text-[11px] text-slate-400 sm:block">⌘K</kbd>
      {open && q.trim() && (
        <div className="animate-in absolute left-0 right-0 top-12 z-40 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
          {results.length === 0 ? (
            <div className="px-4 py-3 text-sm text-slate-500">No conversations match “{q}”. Press Enter to search everything.</div>
          ) : (
            results.map((t) => {
              const theme = agentTheme(t.agent);
              return (
                <Link key={t.thread_id} href={`/chat/${t.thread_id}`} className="flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50">
                  <span className={cn("flex h-7 w-7 items-center justify-center rounded-lg", theme.tint, theme.text)}>
                    {t.agent ? <theme.icon className="h-3.5 w-3.5" /> : <MessagesSquare className="h-3.5 w-3.5" />}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm text-slate-800">{t.title || "Untitled"}</span>
                  <span className="text-xs text-slate-400">{timeAgo(t.updated_at)}</span>
                </Link>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

function UserMenu() {
  const { me } = useSession();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onClick = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);
  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white ring-offset-2 hover:ring-2 hover:ring-slate-300"
        aria-label="Account menu"
      >
        {initials(me.full_name || me.username)}
      </button>
      {open && (
        <div className="animate-in absolute right-0 top-12 z-40 w-60 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
          <div className="border-b border-slate-100 px-4 py-3">
            <div className="truncate text-sm font-semibold text-slate-900">{me.full_name || me.username}</div>
            <div className="text-xs text-slate-500">@{me.username} · {me.role === "admin" ? "Administrator" : "Member"}</div>
          </div>
          <Link href="/settings" onClick={() => setOpen(false)} className="flex items-center gap-2 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50">
            <Settings className="h-4 w-4" /> Settings
          </Link>
          <button onClick={logout} className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50">
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}

export function Topbar({ onMenu }: { onMenu: () => void }) {
  return (
    <header className="sticky top-0 z-30 flex h-[72px] items-center gap-4 border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-7">
      <button onClick={onMenu} className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden" aria-label="Open menu">
        <Menu className="h-5 w-5" />
      </button>
      <GlobalSearch />
      <div className="ml-auto flex items-center gap-3">
        <SystemStatus />
        <UserMenu />
      </div>
    </header>
  );
}
