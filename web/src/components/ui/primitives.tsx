"use client";

import { Loader2, X } from "lucide-react";
import { forwardRef, useEffect, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand text-white hover:bg-brand-hover shadow-sm",
  secondary: "bg-slate-100 text-slate-800 hover:bg-slate-200",
  outline: "bg-white text-slate-800 border border-slate-200 hover:bg-slate-50 shadow-sm",
  ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
  danger: "bg-white text-red-600 border border-red-200 hover:bg-red-50",
};

export const Button = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant; size?: "sm" | "md" | "lg"; loading?: boolean;
}>(function Button({ variant = "primary", size = "md", loading, className, children, disabled, ...props }, ref) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-50",
        size === "sm" && "h-8 px-3 text-sm",
        size === "md" && "h-10 px-4 text-sm",
        size === "lg" && "h-11 px-5 text-[15px]",
        VARIANTS[variant],
        className,
      )}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
});

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("rounded-2xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)]", className)}>{children}</div>;
}

export function CardHeader({ title, description, action }: { title: ReactNode; description?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-5 py-4">
      <div>
        <h3 className="text-[15px] font-semibold text-slate-900">{title}</h3>
        {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function PageHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input({ className, ...props }, ref) {
  return (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400",
        "focus:border-accent/60 focus:outline-none focus:ring-4 focus:ring-accent/10",
        className,
      )}
      {...props}
    />
  );
});

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea({ className, ...props }, ref) {
  return (
    <textarea
      ref={ref}
      className={cn(
        "w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400",
        "focus:border-accent/60 focus:outline-none focus:ring-4 focus:ring-accent/10",
        className,
      )}
      {...props}
    />
  );
});

export function Select({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900",
        "focus:border-accent/60 focus:outline-none focus:ring-4 focus:ring-accent/10",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Label({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <label className="mb-1.5 block text-sm font-medium text-slate-700">
      {children}
      {hint && <span className="ml-1 font-normal text-slate-400">{hint}</span>}
    </label>
  );
}

export function Badge({ children, tone = "slate", className }: { children: ReactNode; tone?: "slate" | "green" | "red" | "amber" | "blue" | "violet"; className?: string }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    green: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200",
    red: "bg-red-50 text-red-700 ring-1 ring-inset ring-red-200",
    amber: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200",
    blue: "bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-200",
    violet: "bg-violet-50 text-violet-700 ring-1 ring-inset ring-violet-200",
  };
  return <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium", tones[tone], className)}>{children}</span>;
}

export function StatusDot({ className }: { className?: string }) {
  return <span className={cn("inline-block h-2 w-2 rounded-full bg-emerald-500", className)} />;
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("h-5 w-5 animate-spin text-slate-400", className)} />;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-xl bg-slate-100", className)} />;
}

export function EmptyState({ icon, title, description, action }: { icon?: ReactNode; title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      {icon && <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">{icon}</div>}
      <p className="font-medium text-slate-900">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Toggle({ checked, onChange, disabled, label }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean; label?: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:opacity-50",
        checked ? "bg-emerald-500" : "bg-slate-200",
      )}
    >
      <span className={cn("inline-block h-5 w-5 rounded-full bg-white shadow transition-transform", checked ? "translate-x-5" : "translate-x-0.5")} />
    </button>
  );
}

export function Modal({ open, onClose, title, children, footer, wide }: {
  open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode; wide?: boolean;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/30 backdrop-blur-[2px]" onClick={onClose} />
      <div className={cn("animate-in relative w-full rounded-2xl bg-white shadow-xl", wide ? "max-w-2xl" : "max-w-md")}>
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-base font-semibold text-slate-900">{title}</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="max-h-[70vh] overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-3">{footer}</div>}
      </div>
    </div>
  );
}

export function Drawer({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: ReactNode; children: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-slate-900/30" onClick={onClose} />
      <aside className="animate-in absolute right-0 top-0 flex h-full w-full max-w-xl flex-col bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <div className="text-base font-semibold text-slate-900">{title}</div>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
      </aside>
    </div>
  );
}

export function Tabs<T extends string>({ value, onChange, items }: { value: T; onChange: (v: T) => void; items: { value: T; label: ReactNode }[] }) {
  return (
    <div className="inline-flex rounded-xl border border-slate-200 bg-white p-1">
      {items.map((it) => (
        <button
          key={it.value}
          onClick={() => onChange(it.value)}
          className={cn(
            "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
            value === it.value ? "bg-brand text-white" : "text-slate-600 hover:text-slate-900",
          )}
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}
