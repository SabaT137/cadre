"use client";

import { createContext, useContext, useEffect, useRef, type ReactNode } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { onAuthChange } from "@/lib/auth-events";
import type { AgentName, Me } from "@/lib/types";

interface Session {
  me: Me;
  isAdmin: boolean;
  can: (agent: AgentName) => boolean;
  refresh: () => void;
}

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children, fallback }: { children: ReactNode; fallback: ReactNode }) {
  const { data, mutate } = useSWR<Me>("/auth/me", fetcher, { revalidateOnFocus: true });
  const userId = useRef<number | null>(null);

  // The session cookie is shared by every tab. If another tab signs in as someone else
  // (or signs out), reload so this tab never shows the previous user's data.
  useEffect(() => onAuthChange((e) => {
    if (e.type === "logout" || e.userId !== userId.current) window.location.reload();
  }), []);
  useEffect(() => {
    if (!data) return;
    if (userId.current !== null && userId.current !== data.id) window.location.reload();
    userId.current = data.id;
  }, [data]);

  if (!data) return <>{fallback}</>;
  const available = new Set(data.available_agents.map((a) => a.name));
  return (
    <SessionContext.Provider
      value={{ me: data, isAdmin: data.role === "admin", can: (a) => available.has(a), refresh: () => mutate() }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): Session {
  const s = useContext(SessionContext);
  if (!s) throw new Error("useSession outside SessionProvider");
  return s;
}
