"use client";

import {
  Activity, BarChart3, Bot, FileText, Home, MessagesSquare, Plug, Settings, ShieldCheck, Users,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AGENT_ORDER, agentTheme } from "@/lib/agents";
import { cn, newThreadId, setPendingPrompt } from "@/lib/utils";
import { Logo } from "./logo";
import { useSession } from "./session";

const MAIN = [
  { href: "/", label: "Home", icon: Home },
  { href: "/agents", label: "AI Agents", icon: Bot },
  { href: "/conversations", label: "My Conversations", icon: MessagesSquare },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/activity", label: "Activity", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

const ADMIN = [
  { href: "/admin", label: "Overview", icon: BarChart3 },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/agents", label: "Agents & access", icon: ShieldCheck },
  { href: "/admin/integrations", label: "Integrations", icon: Plug },
];

function NavLink({ href, label, icon: Icon, active, onClick }: {
  href: string; label: string; icon: typeof Home; active: boolean; onClick?: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className={cn(
        "flex items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] transition-colors",
        active ? "bg-slate-100 font-medium text-slate-900" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
      )}
    >
      <Icon className="h-[18px] w-[18px]" strokeWidth={1.8} />
      {label}
    </Link>
  );
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const { me, isAdmin } = useSession();
  const isActive = (href: string) => (href === "/" || href === "/admin" ? pathname === href : pathname.startsWith(href));
  const agents = AGENT_ORDER.filter((a) => me.available_agents.some((x) => x.name === a));

  function startWith(agent: string) {
    const id = newThreadId();
    setPendingPrompt(id, { message: "", department: agent });
    router.push(`/chat/${id}`);
    onNavigate?.();
  }

  return (
    <div className="flex h-full flex-col">
      <div className="px-5 pb-4 pt-5">
        <Link href="/" onClick={onNavigate}><Logo /></Link>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
        {MAIN.map((item) => <NavLink key={item.href} {...item} active={isActive(item.href)} onClick={onNavigate} />)}

        {isAdmin && (
          <>
            <p className="px-3 pb-1 pt-6 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Admin</p>
            {ADMIN.map((item) => <NavLink key={item.href} {...item} active={isActive(item.href)} onClick={onNavigate} />)}
          </>
        )}

        {agents.length > 0 && (
          <>
            <p className="px-3 pb-2 pt-6 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Agents</p>
            <div className="space-y-0.5">
              {agents.map((name) => {
                const t = agentTheme(name);
                return (
                  <button
                    key={name}
                    onClick={() => startWith(name)}
                    className="group flex w-full items-center gap-3 rounded-xl px-2.5 py-2 text-left hover:bg-slate-50"
                  >
                    <span className={cn("relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full", t.tint, t.text)}>
                      <t.icon className="h-4 w-4" />
                      <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-emerald-500" />
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-slate-900">{t.title}</span>
                      <span className="block truncate text-xs text-slate-500">{t.tagline}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          </>
        )}
      </nav>
    </div>
  );
}
