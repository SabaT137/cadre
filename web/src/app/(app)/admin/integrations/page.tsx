"use client";

import { KanbanSquare } from "lucide-react";
import useSWR from "swr";
import { AdminGuard } from "@/components/admin/admin-guard";
import { Badge, Button, Card, CardHeader, EmptyState, PageHeader, Skeleton } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, fetcher } from "@/lib/api";
import type { JiraConnectionRow, JiraStatus } from "@/lib/types";
import { timeAgo } from "@/lib/utils";

function Integrations() {
  const toast = useToast();
  const { data, mutate } = useSWR<JiraConnectionRow[]>("/admin/integrations", fetcher);
  const { data: status } = useSWR<JiraStatus>("/integrations/jira/status", fetcher);

  async function revoke(c: JiraConnectionRow) {
    if (!confirm(`Revoke Jira access for @${c.user}?`)) return;
    try {
      await api(`/admin/integrations/jira/${c.user_id}`, { method: "DELETE" });
      toast(`Revoked Jira for @${c.user}`, "success");
      mutate();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Revoke failed", "error");
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-8">
      <PageHeader title="Integrations" description="External tools connected by your users." />
      <Card>
        <CardHeader
          title={<span className="flex items-center gap-2"><KanbanSquare className="h-4 w-4 text-teal-600" /> Jira</span>}
          description="Each user connects their own Jira account. The PM agent only reads."
          action={status && <Badge tone={status.oauth_available ? "green" : "amber"}>{status.oauth_available ? "OAuth connector ready" : "OAuth app not configured · API tokens only"}</Badge>}
        />
        {!data ? <div className="p-5"><Skeleton className="h-12" /></div> : data.length === 0 ? (
          <EmptyState title="No Jira connections" description="Users connect Jira from Settings or the PM agent's panel." />
        ) : (
          <ul className="divide-y divide-slate-100">
            {data.map((c) => (
              <li key={c.user_id} className="flex flex-wrap items-center gap-4 px-5 py-4">
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-slate-900">@{c.user}</div>
                  <div className="text-sm text-slate-500">{c.site_url.replace("https://", "")} · as {c.account} · connected {timeAgo(c.connected_at)}</div>
                </div>
                <Badge>{c.auth_type === "oauth" ? "OAuth" : c.auth_type === "pat" ? "PAT" : "API token"}</Badge>
                <Button variant="danger" size="sm" onClick={() => revoke(c)}>Revoke</Button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

export default function AdminIntegrationsPage() {
  return <AdminGuard><Integrations /></AdminGuard>;
}
