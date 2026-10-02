"use client";

import { useState } from "react";
import { SessionProvider } from "@/components/layout/session";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { LogoMark } from "@/components/layout/logo";
import { Spinner } from "@/components/ui/primitives";
import { ToastProvider } from "@/components/ui/toast";

function Loading() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4">
      <LogoMark className="h-14 w-14 animate-pulse" />
      <Spinner />
    </div>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <ToastProvider>
      <SessionProvider fallback={<Loading />}>
        <div className="flex h-full">
          <aside className="hidden w-[285px] shrink-0 border-r border-slate-200 bg-white lg:block">
            <Sidebar />
          </aside>
          {menuOpen && (
            <div className="fixed inset-0 z-40 lg:hidden">
              <div className="absolute inset-0 bg-slate-900/30" onClick={() => setMenuOpen(false)} />
              <aside className="animate-in absolute left-0 top-0 h-full w-[285px] bg-white shadow-xl">
                <Sidebar onNavigate={() => setMenuOpen(false)} />
              </aside>
            </div>
          )}
          <div className="flex min-w-0 flex-1 flex-col">
            <Topbar onMenu={() => setMenuOpen(true)} />
            <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
          </div>
        </div>
      </SessionProvider>
    </ToastProvider>
  );
}
