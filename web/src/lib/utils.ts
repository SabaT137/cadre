import clsx, { type ClassValue } from "clsx";

export const cn = (...inputs: ClassValue[]) => clsx(inputs);

export function newThreadId(): string {
  return crypto.randomUUID().replace(/-/g, "");
}

/** Backend timestamps are naive UTC ("2026-10-02T07:10:36"); treat them as UTC. */
export function parseUtc(iso: string): Date {
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);
}

export function timeAgo(iso: string): string {
  const diff = (Date.now() - parseUtc(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d ago`;
  return parseUtc(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(iso: string): string {
  return parseUtc(iso).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function greeting(date = new Date()): string {
  const h = date.getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? parts[0]?.[1] ?? "")).toUpperCase() || "?";
}

export function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] || name;
}

export function money(amount: number, currency: string): string {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amount);
  } catch {
    return `${currency} ${amount.toFixed(2)}`;
  }
}

export function seconds(ms: number): string {
  return `${(ms / 1000).toFixed(1)}s`;
}

export function fileKind(filename: string): "pdf" | "docx" | "xlsx" | "csv" | "md" | "file" {
  const ext = filename.split(".").pop()?.toLowerCase();
  return ext === "pdf" || ext === "docx" || ext === "xlsx" || ext === "csv" || ext === "md" ? ext : "file";
}

const PENDING_KEY = "cadre:pending:";
export function setPendingPrompt(threadId: string, payload: { message: string; department: string }) {
  try { sessionStorage.setItem(PENDING_KEY + threadId, JSON.stringify(payload)); } catch { /* storage unavailable */ }
}
export function takePendingPrompt(threadId: string): { message: string; department: string } | null {
  try {
    const raw = sessionStorage.getItem(PENDING_KEY + threadId);
    if (!raw) return null;
    sessionStorage.removeItem(PENDING_KEY + threadId);
    return JSON.parse(raw);
  } catch {
    return null;
  }
}
