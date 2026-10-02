"use client";

import { CheckCircle2, ExternalLink, KanbanSquare, Link2 } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";
import { Button, Input, Label, Spinner } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, fetcher } from "@/lib/api";
import type { JiraStatus } from "@/lib/types";
import { timeAgo } from "@/lib/utils";

export function JiraConnection({ compact = false }: { compact?: boolean }) {
  const toast = useToast();
  const { data, mutate, isLoading } = useSWR<JiraStatus>("/integrations/jira/status", fetcher);
  const [site, setSite] = useState("");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [showForm, setShowForm] = useState(false);

  async function connectOAuth() {
    try {
      const { authorize_url } = await api<{ authorize_url: string }>("/integrations/jira/connect");
      window.location.href = authorize_url;
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not start Jira connection", "error");
    }
  }

  async function connectToken(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await api<{ account?: string }>("/integrations/jira/token", { method: "POST", json: { site_url: site, email, api_token: token } });
      toast(`Jira connected${res.account ? ` as ${res.account}` : ""}`, "success");
      setToken("");
      setShowForm(false);
      mutate();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Connection failed", "error");
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    await api("/integrations/jira", { method: "DELETE" });
    toast("Jira disconnected", "info");
    mutate();
  }

  if (isLoading || !data) return <div className="flex justify-center py-6"><Spinner /></div>;

  if (data.connected) {
    return (
      <div className="space-y-3">
        <div className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50/60 p-3">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
          <div className="min-w-0 text-sm">
            <div className="font-medium text-slate-900">Connected to {data.site_url?.replace("https://", "")}</div>
            <div className="text-slate-600">as {data.account} · {data.auth_type === "oauth" ? "OAuth" : data.auth_type === "pat" ? "Personal access token" : "API token"}</div>
            {data.connected_at && !compact && <div className="text-xs text-slate-500">Connected {timeAgo(data.connected_at)}</div>}
          </div>
        </div>
        <div className="flex gap-2">
          <a href={data.site_url} target="_blank" rel="noreferrer" className="inline-flex h-8 items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 hover:bg-slate-50">
            <ExternalLink className="h-3.5 w-3.5" /> Open Jira
          </a>
          <Button variant="danger" size="sm" onClick={disconnect}>Disconnect</Button>
        </div>
        <p className="text-xs text-slate-500">The PM agent has read-only access. It never changes your Jira.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
        <KanbanSquare className="mt-0.5 h-5 w-5 shrink-0 text-teal-600" />
        <p className="text-sm text-slate-600">Connect your Jira so the PM agent can read your projects, sprints and velocity. Access is read-only.</p>
      </div>
      {data.oauth_available && (
        <Button onClick={connectOAuth} className="w-full"><Link2 className="h-4 w-4" /> Connect Jira</Button>
      )}
      {(!data.oauth_available || showForm) ? (
        <form onSubmit={connectToken} className="space-y-3">
          <div>
            <Label>Jira site</Label>
            <Input value={site} onChange={(e) => setSite(e.target.value)} placeholder="yourcompany.atlassian.net" required />
          </div>
          <div>
            <Label>Atlassian email</Label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required />
          </div>
          <div>
            <Label hint={<a className="text-blue-600 hover:underline" href="https://id.atlassian.com/manage-profile/security/api-tokens" target="_blank" rel="noreferrer">Create one</a>}>API token</Label>
            <Input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="Paste your API token" required />
          </div>
          <Button type="submit" variant={data.oauth_available ? "outline" : "primary"} loading={busy} className="w-full">Connect with API token</Button>
        </form>
      ) : (
        <button onClick={() => setShowForm(true)} className="w-full text-center text-xs text-slate-500 hover:text-slate-800">Use an API token instead</button>
      )}
    </div>
  );
}
