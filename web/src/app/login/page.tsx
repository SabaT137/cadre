"use client";

import { ArrowRight, Lock, User, UserCheck } from "lucide-react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { Logo } from "@/components/layout/logo";
import { Button } from "@/components/ui/primitives";
import { AGENT_ORDER, agentTheme } from "@/lib/agents";
import { announceAuthChange } from "@/lib/auth-events";
import type { Me } from "@/lib/types";
import { cn } from "@/lib/utils";

/** If this browser already has a session, say who it belongs to (signing in below replaces it). */
function CurrentSession() {
  const [me, setMe] = useState<Me | null>(null);
  useEffect(() => {
    let alive = true;
    fetch("/api/backend/auth/me", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => alive && setMe(d))
      .catch(() => {});
    return () => { alive = false; };
  }, []);
  if (!me) return null;
  return (
    <div className="mb-6 flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm">
      <UserCheck className="h-4 w-4 shrink-0 text-accent" />
      <span className="min-w-0 flex-1 text-slate-600">
        Signed in as <span className="font-medium text-slate-900">{me.full_name || me.username}</span> (@{me.username}).
        Sign in below to switch account.
      </span>
      <Link href="/" className="shrink-0 font-medium text-slate-900 hover:underline">Continue →</Link>
    </div>
  );
}

function LoginForm() {
  const params = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ username: username.trim(), password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Sign in failed");
      announceAuthChange({ type: "login", userId: data.user?.id });
      const next = params.get("next");
      window.location.href = next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="username">Username</label>
        <div className="relative">
          <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            id="username" autoComplete="username" autoFocus value={username} onChange={(e) => setUsername(e.target.value)}
            className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm focus:border-accent/60 focus:outline-none focus:ring-4 focus:ring-accent/10"
            placeholder="your.username"
          />
        </div>
      </div>
      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="password">Password</label>
        <div className="relative">
          <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)}
            className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm focus:border-accent/60 focus:outline-none focus:ring-4 focus:ring-accent/10"
            placeholder="••••••••"
          />
        </div>
      </div>
      {error && <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      <Button type="submit" size="lg" className="w-full" loading={loading} disabled={!username || !password}>
        Sign in <ArrowRight className="h-4 w-4" />
      </Button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="grid min-h-full lg:grid-cols-2">
      <div className="flex flex-col justify-between bg-white px-6 py-8 sm:px-12">
        <Logo size="lg" />
        <div className="mx-auto w-full max-w-sm py-12">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Welcome back</h1>
          <p className="mb-8 mt-2 text-slate-500">Sign in to Cadre, your AI workspace.</p>
          <CurrentSession />
          <Suspense>
            <LoginForm />
          </Suspense>
          <p className="mt-6 text-center text-xs text-slate-400">Accounts are managed by your workspace administrator.</p>
        </div>
        <p className="text-xs text-slate-400">© {new Date().getFullYear()} Stixor Technologies</p>
      </div>
      <div className="relative hidden overflow-hidden bg-slate-50 lg:flex lg:items-center lg:justify-center">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,#e0f5f6,transparent_45%),radial-gradient(circle_at_80%_70%,#e8edf2,transparent_50%)]" />
        <div className="relative max-w-md px-10">
          <p className="text-sm font-medium text-slate-500">Your AI team</p>
          <h2 className="mt-2 text-3xl font-semibold leading-tight text-slate-900">One workspace. Five specialist agents.</h2>
          <div className="mt-8 space-y-3">
            {AGENT_ORDER.map((name) => {
              const t = agentTheme(name);
              return (
                <div key={name} className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 shadow-sm backdrop-blur">
                  <span className={cn("flex h-9 w-9 items-center justify-center rounded-xl", t.tint, t.text)}>
                    <t.icon className="h-4 w-4" />
                  </span>
                  <div>
                    <div className="text-sm font-semibold text-slate-900">{t.title}</div>
                    <div className="text-xs text-slate-500">{t.capabilities.slice(0, 3).join(" · ")}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
