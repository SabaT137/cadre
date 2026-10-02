import { Hexagon } from "lucide-react";

export function Logo({ subtitle = "AI Workspace" }: { subtitle?: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900 text-white shadow-sm">
        <Hexagon className="h-5 w-5" strokeWidth={2.25} />
      </div>
      <div className="leading-tight">
        <div className="text-[15px] font-semibold text-slate-900">Nexus</div>
        <div className="text-xs text-slate-500">{subtitle}</div>
      </div>
    </div>
  );
}
