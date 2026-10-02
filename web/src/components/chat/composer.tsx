"use client";

import { ArrowUp, Check, ChevronDown, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useSession } from "@/components/layout/session";
import { AGENT_ORDER, agentTheme } from "@/lib/agents";
import type { Department } from "@/lib/types";
import { cn } from "@/lib/utils";

function AgentPicker({ value, onChange }: { value: Department; onChange: (d: Department) => void }) {
  const { me } = useSession();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onClick = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);
  const options: Department[] = ["auto", ...AGENT_ORDER.filter((a) => me.available_agents.some((x) => x.name === a))];
  const current = value === "auto" ? null : agentTheme(value);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-[13px] text-slate-500 hover:bg-slate-100 hover:text-slate-800"
      >
        {current ? (
          <>
            <current.icon className={cn("h-3.5 w-3.5", current.text)} />
            <span className="font-medium text-slate-700">{current.title}</span>
          </>
        ) : (
          <>
            <Sparkles className="h-3.5 w-3.5" />
            The orchestrator picks the right agent
          </>
        )}
        <ChevronDown className="h-3.5 w-3.5" />
      </button>
      {open && (
        <div className="animate-in absolute bottom-9 left-0 z-30 w-72 overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-lg">
          {options.map((opt) => {
            const t = opt === "auto" ? null : agentTheme(opt);
            return (
              <button
                key={opt}
                type="button"
                onClick={() => { onChange(opt); setOpen(false); }}
                className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-slate-50"
              >
                <span className={cn("flex h-7 w-7 items-center justify-center rounded-lg", t ? `${t.tint} ${t.text}` : "bg-slate-100 text-slate-600")}>
                  {t ? <t.icon className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5" />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-slate-900">{t ? t.title : "Auto"}</span>
                  <span className="block truncate text-xs text-slate-500">{t ? t.tagline : "Let the orchestrator route it"}</span>
                </span>
                {value === opt && <Check className="h-4 w-4 text-slate-900" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function Composer({
  onSubmit, department, onDepartmentChange, disabled, placeholder = "Ask anything or describe a task…",
  variant = "hero", autoFocus, value, onValueChange,
}: {
  onSubmit: (text: string) => void;
  department: Department;
  onDepartmentChange: (d: Department) => void;
  disabled?: boolean;
  placeholder?: string;
  variant?: "hero" | "dock";
  autoFocus?: boolean;
  value?: string;
  onValueChange?: (v: string) => void;
}) {
  const [inner, setInner] = useState("");
  const text = value ?? inner;
  const setText = onValueChange ?? setInner;
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 240)}px`;
  }, [text]);

  function submit() {
    const t = text.trim();
    if (!t || disabled) return;
    onSubmit(t);
    setText("");
  }

  return (
    <div className={cn(
      "rounded-2xl border border-slate-200 bg-white shadow-[0_1px_3px_rgba(15,23,42,0.06)] transition focus-within:border-accent/50 focus-within:shadow-[0_4px_16px_rgba(15,23,42,0.06)]",
      variant === "hero" ? "p-4" : "p-3",
    )}>
      <textarea
        ref={ref}
        value={text}
        autoFocus={autoFocus}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            submit();
          }
        }}
        rows={variant === "hero" ? 3 : 1}
        placeholder={placeholder}
        className={cn(
          "w-full resize-none bg-transparent px-2 text-slate-900 placeholder:text-slate-400 focus:outline-none",
          variant === "hero" ? "min-h-[84px] text-[17px]" : "min-h-[28px] text-[15px]",
        )}
      />
      <div className="mt-2 flex items-center justify-between gap-3">
        <AgentPicker value={department} onChange={onDepartmentChange} />
        <button
          type="button"
          onClick={submit}
          disabled={!text.trim() || disabled}
          aria-label="Send"
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-xl transition-colors",
            text.trim() && !disabled ? "bg-brand text-white hover:bg-brand-hover" : "bg-slate-400/80 text-white",
          )}
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
