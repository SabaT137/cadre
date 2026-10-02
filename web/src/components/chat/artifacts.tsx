"use client";

import { ChevronDown, Database, Download, ExternalLink, FileSpreadsheet, FileText, FileType2, Table2 } from "lucide-react";
import { useState } from "react";
import { DataTable } from "@/components/ui/data-table";
import { fileUrl } from "@/lib/api";
import type { Artifact, FileArtifact, SqlArtifact, TableArtifact } from "@/lib/types";
import { cn, fileKind } from "@/lib/utils";

const FILE_STYLE = {
  pdf: { icon: FileType2, tint: "bg-red-50 text-red-600", label: "PDF document" },
  docx: { icon: FileText, tint: "bg-blue-50 text-blue-600", label: "Word document" },
  xlsx: { icon: FileSpreadsheet, tint: "bg-emerald-50 text-emerald-600", label: "Excel workbook" },
  csv: { icon: FileSpreadsheet, tint: "bg-emerald-50 text-emerald-600", label: "CSV file" },
  md: { icon: FileText, tint: "bg-slate-100 text-slate-600", label: "Markdown file" },
  file: { icon: FileText, tint: "bg-slate-100 text-slate-600", label: "File" },
};

export function FileCard({ a }: { a: FileArtifact }) {
  const kind = fileKind(a.filename);
  const s = FILE_STYLE[kind];
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <span className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-lg", s.tint)}>
        <s.icon className="h-5 w-5" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium text-slate-900">{a.filename}</div>
        <div className="text-xs text-slate-500">{a.invoice_no ? `Invoice ${a.invoice_no}` : s.label}</div>
      </div>
      {kind === "pdf" && (
        <a href={fileUrl(a.file_id, true)} target="_blank" rel="noreferrer"
           className="flex h-9 items-center gap-1.5 rounded-lg px-3 text-sm text-slate-600 hover:bg-slate-100">
          <ExternalLink className="h-4 w-4" /> Preview
        </a>
      )}
      <a href={fileUrl(a.file_id)} download={a.filename}
         className="flex h-9 items-center gap-1.5 rounded-lg bg-brand px-3 text-sm font-medium text-white hover:bg-brand-hover">
        <Download className="h-4 w-4" /> Download
      </a>
    </div>
  );
}

function Collapsible({ icon: Icon, title, children, defaultOpen = false }: {
  icon: typeof Database; title: string; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm font-medium text-slate-700 hover:bg-slate-50">
        <Icon className="h-4 w-4 text-slate-500" />
        <span className="flex-1">{title}</span>
        <ChevronDown className={cn("h-4 w-4 text-slate-400 transition", open && "rotate-180")} />
      </button>
      {open && <div className="space-y-3 border-t border-slate-100 p-3">{children}</div>}
    </div>
  );
}

function SqlView({ a }: { a: SqlArtifact }) {
  return (
    <Collapsible icon={Database} title={`Query result · ${a.rows.length} row${a.rows.length === 1 ? "" : "s"}`} defaultOpen={a.rows.length > 0 && a.rows.length <= 25}>
      <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 font-mono text-xs text-slate-100">{a.query}</pre>
      {a.rows.length > 0 && <DataTable columns={a.columns} rows={a.rows} maxHeight={360} />}
    </Collapsible>
  );
}

function TableView({ a }: { a: TableArtifact }) {
  const sprintCol = a.columns.indexOf("Sprint");
  return (
    <Collapsible icon={Table2} title={`${a.title} · ${a.rows.length} rows`} defaultOpen>
      <DataTable
        columns={a.columns}
        rows={a.rows}
        maxHeight={420}
        highlight={sprintCol >= 0 ? (r) => String(r[sprintCol] ?? "").startsWith("Overflow") : undefined}
      />
    </Collapsible>
  );
}

export function Artifacts({ items }: { items: Artifact[] }) {
  if (!items?.length) return null;
  return (
    <div className="mt-3 space-y-2">
      {items.map((a, i) =>
        a.type === "file" ? <FileCard key={i} a={a} /> : a.type === "sql" ? <SqlView key={i} a={a} /> : <TableView key={i} a={a} />,
      )}
    </div>
  );
}
