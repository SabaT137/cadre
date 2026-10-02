"use client";

import { Check, Pencil, Plus } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";
import { AdminGuard } from "@/components/admin/admin-guard";
import { useSession } from "@/components/layout/session";
import { Badge, Button, Card, Input, Label, Modal, PageHeader, Select, Skeleton, Toggle } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, fetcher } from "@/lib/api";
import { AGENT_ORDER, agentTheme } from "@/lib/agents";
import type { AdminUser, AgentName } from "@/lib/types";
import { cn, initials, timeAgo } from "@/lib/utils";

function AgentPicker({ value, onChange }: { value: AgentName[]; onChange: (v: AgentName[]) => void }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {AGENT_ORDER.map((a) => {
        const t = agentTheme(a);
        const on = value.includes(a);
        return (
          <button
            key={a}
            type="button"
            onClick={() => onChange(on ? value.filter((x) => x !== a) : [...value, a])}
            className={cn("flex items-center gap-2 rounded-xl border px-3 py-2 text-left text-sm transition", on ? "border-brand bg-brand-soft/60" : "border-slate-200 hover:bg-slate-50")}
          >
            <span className={cn("flex h-7 w-7 items-center justify-center rounded-lg", t.tint, t.text)}><t.icon className="h-3.5 w-3.5" /></span>
            <span className="flex-1 font-medium text-slate-800">{t.label}</span>
            {on && <Check className="h-4 w-4 text-slate-900" />}
          </button>
        );
      })}
    </div>
  );
}

interface FormState { username: string; full_name: string; password: string; role: "admin" | "user"; allowed_agents: AgentName[]; is_active: boolean }
const EMPTY: FormState = { username: "", full_name: "", password: "", role: "user", allowed_agents: [], is_active: true };

function Users() {
  const toast = useToast();
  const { me } = useSession();
  const { data, mutate } = useSWR<AdminUser[]>("/admin/users", fetcher);
  const [editing, setEditing] = useState<AdminUser | "new" | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [saving, setSaving] = useState(false);

  function open(u: AdminUser | "new") {
    setEditing(u);
    setForm(u === "new" ? EMPTY : { username: u.username, full_name: u.full_name, password: "", role: u.role, allowed_agents: u.allowed_agents, is_active: u.is_active });
  }

  async function save() {
    setSaving(true);
    try {
      if (editing === "new") {
        await api("/admin/users", { method: "POST", json: { username: form.username, full_name: form.full_name, password: form.password, role: form.role, allowed_agents: form.allowed_agents } });
        toast(`Created @${form.username.toLowerCase()}`, "success");
      } else if (editing) {
        const body: Record<string, unknown> = { full_name: form.full_name, role: form.role, allowed_agents: form.allowed_agents, is_active: form.is_active };
        if (form.password) body.password = form.password;
        await api(`/admin/users/${editing.id}`, { method: "PATCH", json: body });
        toast("User updated", "success");
      }
      setEditing(null);
      mutate();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Save failed", "error");
    } finally {
      setSaving(false);
    }
  }

  const isNew = editing === "new";
  const isSelf = editing !== "new" && editing?.id === me.id;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-8">
      <PageHeader title="Users" description="Who can sign in, and which agents each person can use." action={<Button onClick={() => open("new")}><Plus className="h-4 w-4" /> New user</Button>} />
      <Card>
        {!data ? <div className="space-y-3 p-5">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-12" />)}</div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-100 bg-slate-50/60 text-slate-500">
                <tr>{["User", "Role", "Agents", "Jira", "Status", "Created", ""].map((h) => <th key={h} className="px-5 py-3 font-medium">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/60">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand text-xs font-semibold text-white">{initials(u.full_name || u.username)}</span>
                        <div>
                          <div className="font-medium text-slate-900">{u.full_name || u.username}</div>
                          <div className="text-xs text-slate-500">@{u.username}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3"><Badge tone={u.role === "admin" ? "violet" : "slate"}>{u.role}</Badge></td>
                    <td className="px-5 py-3">
                      <div className="flex flex-wrap gap-1">
                        {u.role === "admin" ? <span className="text-xs text-slate-500">All agents</span> : u.allowed_agents.length === 0 ? <span className="text-xs text-slate-400">None</span> :
                          u.allowed_agents.map((a) => { const t = agentTheme(a); return <span key={a} className={cn("rounded-md px-1.5 py-0.5 text-xs font-medium", t.tint, t.text)}>{t.label}</span>; })}
                      </div>
                    </td>
                    <td className="px-5 py-3">{u.jira_connected ? <Badge tone="green">Connected</Badge> : <span className="text-xs text-slate-400">—</span>}</td>
                    <td className="px-5 py-3">{u.is_active ? <Badge tone="green">Active</Badge> : <Badge tone="red">Disabled</Badge>}</td>
                    <td className="px-5 py-3 text-slate-500">{timeAgo(u.created_at)}</td>
                    <td className="px-5 py-3 text-right">
                      <button onClick={() => open(u)} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-900" aria-label={`Edit ${u.username}`}><Pencil className="h-4 w-4" /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal
        open={!!editing}
        onClose={() => setEditing(null)}
        title={isNew ? "New user" : `Edit @${typeof editing === "object" && editing ? editing.username : ""}`}
        footer={<><Button variant="ghost" onClick={() => setEditing(null)}>Cancel</Button><Button onClick={save} loading={saving} disabled={isNew && (!form.username || form.password.length < 4)}>{isNew ? "Create user" : "Save changes"}</Button></>}
      >
        <div className="space-y-4">
          {isNew && (
            <div>
              <Label>Username</Label>
              <Input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} placeholder="jane.doe" autoFocus />
            </div>
          )}
          <div>
            <Label>Full name</Label>
            <Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} placeholder="Jane Doe" />
          </div>
          <div>
            <Label hint={isNew ? "(min 4 characters)" : "(leave blank to keep)"}>{isNew ? "Password" : "Reset password"}</Label>
            <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </div>
          <div>
            <Label>Role</Label>
            <Select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as "admin" | "user" })} disabled={isSelf}>
              <option value="user">Member: only the agents selected below</option>
              <option value="admin">Administrator: every agent plus admin pages</option>
            </Select>
          </div>
          {form.role === "user" && (
            <div>
              <Label>Allowed agents</Label>
              <AgentPicker value={form.allowed_agents} onChange={(v) => setForm({ ...form, allowed_agents: v })} />
            </div>
          )}
          {!isNew && (
            <label className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2.5">
              <span className="text-sm font-medium text-slate-700">Account active</span>
              <Toggle checked={form.is_active} onChange={(v) => setForm({ ...form, is_active: v })} disabled={isSelf} label="Active" />
            </label>
          )}
        </div>
      </Modal>
    </div>
  );
}

export default function UsersPage() {
  return <AdminGuard><Users /></AdminGuard>;
}
