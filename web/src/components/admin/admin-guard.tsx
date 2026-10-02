"use client";

import { ShieldAlert } from "lucide-react";
import { useSession } from "@/components/layout/session";
import { Card, EmptyState } from "@/components/ui/primitives";

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const { isAdmin } = useSession();
  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-xl px-4 py-16">
        <Card><EmptyState icon={<ShieldAlert className="h-5 w-5" />} title="Administrators only" description="You don't have access to this page." /></Card>
      </div>
    );
  }
  return <>{children}</>;
}
