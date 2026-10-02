/* eslint-disable @next/next/no-img-element -- small static brand assets; next/image adds nothing here */

/** Full Cadre wordmark (mark + "CADRE"). */
export function Logo({ size = "md", subtitle }: { size?: "sm" | "md" | "lg"; subtitle?: string }) {
  const height = size === "lg" ? "h-11" : size === "sm" ? "h-7" : "h-9";
  return (
    <div className="flex flex-col items-start gap-1">
      <img src="/brand/cadre-logo.png" alt="Cadre" className={`${height} w-auto select-none`} draggable={false} />
      {subtitle && <span className="pl-0.5 text-xs text-slate-500">{subtitle}</span>}
    </div>
  );
}

/** Hexagon network mark only, for tight spaces and loading states. */
export function LogoMark({ className = "h-10 w-10" }: { className?: string }) {
  return <img src="/brand/cadre-mark.png" alt="Cadre" className={`${className} select-none`} draggable={false} />;
}
