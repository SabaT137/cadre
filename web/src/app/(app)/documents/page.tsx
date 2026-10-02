"use client";

import { Download, ExternalLink, FileSpreadsheet, FileText, FileType2, MessageSquare, Upload } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import useSWR from "swr";
import { useSession } from "@/components/layout/session";
import { Badge, Card, EmptyState, PageHeader, Skeleton, Spinner, Tabs, Toggle } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, fetcher, fileUrl } from "@/lib/api";
import { agentTheme } from "@/lib/agents";
import type { DocumentInfo, InvoiceSummary, TemplateInfo } from "@/lib/types";
import { cn, fileKind, formatDateTime, money, timeAgo } from "@/lib/utils";

const ICON = { pdf: FileType2, docx: FileText, xlsx: FileSpreadsheet, csv: FileSpreadsheet, md: FileText, file: FileText };
const TINT = { pdf: "bg-red-50 text-red-600", docx: "bg-blue-50 text-blue-600", xlsx: "bg-emerald-50 text-emerald-600", csv: "bg-emerald-50 text-emerald-600", md: "bg-slate-100 text-slate-600", file: "bg-slate-100 text-slate-600" };

function GeneratedFiles() {
  const { isAdmin } = useSession();
  const [all, setAll] = useState(false);
  const { data } = useSWR<DocumentInfo[]>(`/documents?limit=200${all ? "&scope=all" : ""}`, fetcher);
  return (
    <Card>
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
        <p className="text-sm text-slate-500">Contracts, invoices and plans your agents produced.</p>
        {isAdmin && <label className="flex items-center gap-2 text-sm text-slate-600"><Toggle checked={all} onChange={setAll} label="All users" /> All users</label>}
      </div>
      {!data ? <div className="space-y-3 p-5">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-12" />)}</div> : data.length === 0 ? (
        <EmptyState icon={<FileText className="h-5 w-5" />} title="No documents yet" description="Ask the HR, Finance or PM agent to create a contract, invoice or plan." />
      ) : (
        <ul className="divide-y divide-slate-100">
          {data.map((d) => {
            const kind = fileKind(d.filename);
            const Icon = ICON[kind];
            const theme = agentTheme(d.agent);
            return (
              <li key={d.file_id} className="flex items-center gap-4 px-5 py-3.5">
                <span className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl", TINT[kind])}><Icon className="h-5 w-5" /></span>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium text-slate-900">{d.filename}</div>
                  <div className="flex flex-wrap items-center gap-2 text-sm text-slate-500">
                    <span className={cn("inline-flex items-center gap-1", theme.text)}><theme.icon className="h-3.5 w-3.5" />{theme.label}</span>
                    <span>·</span><span className="capitalize">{d.kind}</span>
                    {all && <><span>·</span><span>@{d.owner}</span></>}
                    <span>·</span><span title={formatDateTime(d.created_at)}>{timeAgo(d.created_at)}</span>
                  </div>
                </div>
                {d.thread_id && <Link href={`/chat/${d.thread_id}`} className="hidden rounded-lg p-2 text-slate-500 hover:bg-slate-100 sm:block" title="Open conversation"><MessageSquare className="h-4 w-4" /></Link>}
                {kind === "pdf" && <a href={fileUrl(d.file_id, true)} target="_blank" rel="noreferrer" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" title="Preview"><ExternalLink className="h-4 w-4" /></a>}
                <a href={fileUrl(d.file_id)} className="inline-flex h-9 items-center gap-1.5 rounded-xl border border-slate-200 px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"><Download className="h-4 w-4" /> Download</a>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

function Templates() {
  const toast = useToast();
  const { data, mutate } = useSWR<TemplateInfo[]>("/templates", fetcher);
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  async function upload(file: File) {
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("name", file.name.replace(/\.docx$/i, ""));
      const t = await api<TemplateInfo>("/templates", { method: "POST", body: form });
      toast(`Uploaded “${t.name}” with ${t.placeholder_count} fields`, "success");
      mutate();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Upload failed", "error");
    } finally {
      setBusy(false);
      if (ref.current) ref.current.value = "";
    }
  }
  return (
    <Card>
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
        <p className="text-sm text-slate-500">Word templates the HR agent fills. Placeholders like [●] are detected automatically.</p>
        <input ref={ref} type="file" accept=".docx" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
        <button onClick={() => ref.current?.click()} disabled={busy} className="inline-flex h-9 items-center gap-2 rounded-xl bg-brand px-3 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-50">
          {busy ? <Spinner className="h-4 w-4 text-white" /> : <Upload className="h-4 w-4" />} Upload template
        </button>
      </div>
      {!data ? <div className="p-5"><Skeleton className="h-12" /></div> : (
        <ul className="divide-y divide-slate-100">
          {data.map((t) => (
            <li key={t.template_id} className="flex items-center gap-4 px-5 py-3.5">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-600"><FileText className="h-5 w-5" /></span>
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium text-slate-900">{t.name}</div>
                <div className="truncate text-sm text-slate-500">{t.description || "No description"}</div>
              </div>
              <Badge>{t.placeholder_count} fields</Badge>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function Invoices() {
  const { data } = useSWR<InvoiceSummary[]>("/invoices?limit=100", fetcher);
  return (
    <Card>
      {!data ? <div className="p-5"><Skeleton className="h-12" /></div> : data.length === 0 ? (
        <EmptyState icon={<FileType2 className="h-5 w-5" />} title="No invoices yet" description="Ask the Finance agent to create one." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-100 bg-slate-50/60 text-slate-500">
              <tr>{["Invoice", "Client", "Service", "Issued", "Total", ""].map((h) => <th key={h} className="px-5 py-3 font-medium">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((inv) => (
                <tr key={inv.invoice_no} className="hover:bg-slate-50/60">
                  <td className="px-5 py-3 font-medium text-slate-900">{inv.invoice_no}</td>
                  <td className="px-5 py-3 text-slate-700">{inv.client}</td>
                  <td className="max-w-[260px] truncate px-5 py-3 text-slate-500">{inv.service_description}</td>
                  <td className="px-5 py-3 text-slate-500">{inv.issue_date}</td>
                  <td className="px-5 py-3 font-semibold text-slate-900">{money(inv.total, inv.currency)}</td>
                  <td className="px-5 py-3 text-right">
                    <a href={fileUrl(inv.file_id, true)} target="_blank" rel="noreferrer" className="mr-3 text-slate-500 hover:text-slate-900">Preview</a>
                    <a href={fileUrl(inv.file_id)} className="font-medium text-slate-700 hover:text-slate-900">Download</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

export default function DocumentsPage() {
  const { can } = useSession();
  const tabs = [
    { value: "files" as const, label: "Generated files" },
    ...(can("hr") ? [{ value: "templates" as const, label: "Contract templates" }] : []),
    ...(can("finance") ? [{ value: "invoices" as const, label: "Invoices" }] : []),
  ];
  const [tab, setTab] = useState<"files" | "templates" | "invoices">("files");
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-8">
      <PageHeader title="Documents" description="Everything your agents have produced, plus the templates they work from." />
      {tabs.length > 1 && <div className="mb-4"><Tabs value={tab} onChange={setTab} items={tabs} /></div>}
      {tab === "files" && <GeneratedFiles />}
      {tab === "templates" && <Templates />}
      {tab === "invoices" && <Invoices />}
    </div>
  );
}
