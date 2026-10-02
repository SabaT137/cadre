"use client";

import { FileText, Upload } from "lucide-react";
import { useRef, useState } from "react";
import useSWR from "swr";
import { JiraConnection } from "@/components/agents/jira-card";
import { Spinner } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, fetcher, fileUrl } from "@/lib/api";
import { agentTheme } from "@/lib/agents";
import type { AgentName, InvoiceSummary, TemplateInfo } from "@/lib/types";
import { cn, money } from "@/lib/utils";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4">
      <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</h4>
      {children}
    </section>
  );
}

function HrTemplates({ templateId, onTemplate }: { templateId: string | null; onTemplate: (id: string | null) => void }) {
  const toast = useToast();
  const { data, mutate } = useSWR<TemplateInfo[]>("/templates", fetcher);
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  async function upload(file: File) {
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("name", file.name.replace(/\.docx$/i, ""));
      const t = await api<TemplateInfo>("/templates", { method: "POST", body: form });
      toast(`Uploaded “${t.name}” (${t.placeholder_count} fields)`, "success");
      await mutate();
      onTemplate(t.template_id);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Upload failed", "error");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <Section title="Contract template">
      {!data ? <Spinner /> : (
        <div className="space-y-1.5">
          <button
            onClick={() => onTemplate(null)}
            className={cn("w-full rounded-xl border px-3 py-2 text-left text-sm", templateId === null ? "border-brand bg-brand-soft/60" : "border-slate-200 hover:bg-slate-50")}
          >
            <span className="font-medium text-slate-800">Let the agent choose</span>
          </button>
          {data.map((t) => (
            <button
              key={t.template_id}
              onClick={() => onTemplate(t.template_id)}
              className={cn("flex w-full items-start gap-2 rounded-xl border px-3 py-2 text-left text-sm", templateId === t.template_id ? "border-brand bg-brand-soft/60" : "border-slate-200 hover:bg-slate-50")}
            >
              <FileText className="mt-0.5 h-4 w-4 shrink-0 text-violet-500" />
              <span className="min-w-0">
                <span className="block truncate font-medium text-slate-800">{t.name}</span>
                <span className="text-xs text-slate-500">{t.placeholder_count} fields</span>
              </span>
            </button>
          ))}
        </div>
      )}
      <input ref={fileRef} type="file" accept=".docx" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
      <button
        onClick={() => fileRef.current?.click()}
        disabled={uploading}
        className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 px-3 py-2.5 text-sm text-slate-600 hover:border-slate-400 hover:bg-slate-50 disabled:opacity-50"
      >
        {uploading ? <Spinner className="h-4 w-4" /> : <Upload className="h-4 w-4" />} Upload .docx template
      </button>
    </Section>
  );
}

function FinanceInvoices() {
  const { data } = useSWR<InvoiceSummary[]>("/invoices?limit=6", fetcher);
  return (
    <Section title="Recent invoices">
      {!data ? <Spinner /> : data.length === 0 ? <p className="text-sm text-slate-500">No invoices yet.</p> : (
        <ul className="space-y-2">
          {data.map((inv) => (
            <li key={inv.invoice_no}>
              <a href={fileUrl(inv.file_id, true)} target="_blank" rel="noreferrer" className="block rounded-xl border border-slate-200 px-3 py-2 hover:bg-slate-50">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-slate-800">{inv.invoice_no}</span>
                  <span className="font-semibold text-slate-900">{money(inv.total, inv.currency)}</span>
                </div>
                <div className="truncate text-xs text-slate-500">{inv.client} · {inv.issue_date}</div>
              </a>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

export function ContextPanel({ agent, templateId, onTemplate, onExample }: {
  agent: AgentName | null;
  templateId: string | null;
  onTemplate: (id: string | null) => void;
  onExample: (prompt: string) => void;
}) {
  const t = agentTheme(agent);
  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-3">
          <span className={cn("flex h-10 w-10 items-center justify-center rounded-xl", t.tint, t.text)}><t.icon className="h-5 w-5" /></span>
          <div>
            <div className="text-sm font-semibold text-slate-900">{agent ? t.title : "Orchestrator"}</div>
            <div className="text-xs text-slate-500">{agent ? t.tagline : "Routes each message to the right agent"}</div>
          </div>
        </div>
        {agent && (
          <div className="mt-4 space-y-1.5">
            {t.examples.map((ex) => (
              <button key={ex} onClick={() => onExample(ex)} className="block w-full rounded-xl bg-slate-50 px-3 py-2 text-left text-[13px] text-slate-600 hover:bg-slate-100">
                {ex}
              </button>
            ))}
          </div>
        )}
      </section>
      {agent === "hr" && <HrTemplates templateId={templateId} onTemplate={onTemplate} />}
      {agent === "finance" && <FinanceInvoices />}
      {agent === "pm" && <Section title="Jira"><JiraConnection compact /></Section>}
    </div>
  );
}
