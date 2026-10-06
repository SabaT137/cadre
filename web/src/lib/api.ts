"use client";

import { announceAuthChange } from "./auth-events";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function detailMessage(data: unknown, fallback: string): string {
  if (data && typeof data === "object" && "detail" in data) {
    const d = (data as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((e) => (e as { msg?: string }).msg ?? "Invalid value").join("; ");
  }
  return fallback;
}

let signingOut = false;

export function goToLogin() {
  // During sign-out, background requests 401 too; let logout() do the redirect (without a ?next=).
  if (signingOut) return;
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    const next = window.location.pathname + window.location.search;
    // Full reload on purpose: drops all cached SWR data from the expired session.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = `/login${next && next !== "/" ? `?next=${encodeURIComponent(next)}` : ""}`;
  }
}

/** Call the FastAPI backend through the Next.js proxy (/api/backend/*). */
export async function api<T = unknown>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  const res = await fetch(`/api/backend${path}`, {
    ...rest,
    headers: json !== undefined ? { "content-type": "application/json", ...headers } : headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
    cache: "no-store",
  });
  if (res.status === 401) {
    goToLogin();
    throw new ApiError(401, "Your session has expired. Please sign in again.");
  }
  const isJson = res.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await res.json() : await res.text();
  if (!res.ok) throw new ApiError(res.status, detailMessage(data, `Request failed (${res.status})`));
  return data as T;
}

/** SWR fetcher */
export const fetcher = <T,>(path: string) => api<T>(path);

export const fileUrl = (fileId: string, inline = false) =>
  `/api/backend/files/${encodeURIComponent(fileId)}${inline ? "?inline=true" : ""}`;

export async function logout() {
  signingOut = true;
  await fetch("/api/auth/logout", { method: "POST" });
  announceAuthChange({ type: "logout" });
  // Full reload on purpose: clears every cached response from the signed-out session.
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.href = "/login";
}
