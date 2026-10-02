"use client";

import Link from "next/link";
import useSWR from "swr";
import { RunsTable } from "@/components/admin/runs-table";
import { useSession } from "@/components/layout/session";
import { Card, PageHeader, Skeleton } from "@/components/ui/primitives";
import { fetcher } from "@/lib/api";
import type { AgentRunRow } from "@/lib/types";

export default function ActivityPage() {
  const { isAdmin } = useSession();
  const { data } = useSWR<AgentRunRow[]>("/activity?limit=100", fetcher, { refreshInterval: 30_000 });
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-8">
      <PageHeader
        title="Activity"
        description="Your recent requests: which agent handled each one, how long it took, and the steps it took."
        action={isAdmin ? <Link href="/admin" className="text-sm font-medium text-blue-600 hover:underline">Workspace-wide activity →</Link> : undefined}
      />
      <Card>
        {!data ? <div className="space-y-3 p-5">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-10" />)}</div> : <RunsTable runs={data} />}
      </Card>
    </div>
  );
}
