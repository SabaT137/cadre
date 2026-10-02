"use client";

import { ArrowDown, ArrowUp } from "lucide-react";
import { useMemo, useState } from "react";
import { cn } from "@/lib/utils";

type Cell = string | number | null;

export function DataTable({ columns, rows, maxHeight = 420, highlight }: {
  columns: string[];
  rows: Cell[][];
  maxHeight?: number;
  highlight?: (row: Cell[]) => boolean;
}) {
  const [sort, setSort] = useState<{ col: number; dir: 1 | -1 } | null>(null);
  const sorted = useMemo(() => {
    if (!sort) return rows;
    return [...rows].sort((a, b) => {
      const x = a[sort.col], y = b[sort.col];
      if (x === y) return 0;
      if (x === null) return 1;
      if (y === null) return -1;
      return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y))) * sort.dir;
    });
  }, [rows, sort]);

  return (
    <div className="overflow-auto rounded-xl border border-slate-200" style={{ maxHeight }}>
      <table className="w-full border-collapse text-left text-[13px]">
        <thead className="sticky top-0 z-10 bg-slate-50">
          <tr>
            {columns.map((c, i) => (
              <th
                key={c + i}
                onClick={() => setSort((s) => (s?.col === i ? (s.dir === 1 ? { col: i, dir: -1 } : null) : { col: i, dir: 1 }))}
                className="cursor-pointer select-none whitespace-nowrap border-b border-slate-200 px-3 py-2 font-semibold text-slate-600 hover:text-slate-900"
              >
                <span className="inline-flex items-center gap-1">
                  {c}
                  {sort?.col === i && (sort.dir === 1 ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, ri) => (
            <tr key={ri} className={cn("border-b border-slate-100 last:border-0", highlight?.(r) ? "bg-amber-50/70" : "hover:bg-slate-50/60")}>
              {r.map((v, ci) => (
                <td key={ci} className="max-w-[360px] truncate px-3 py-2 text-slate-700" title={v === null ? "" : String(v)}>
                  {v === null || v === "" ? <span className="text-slate-300">—</span> : String(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
