"use client";

// All tabs of one browser share the session cookie. When the account changes in one tab,
// tell the others so they reload instead of showing the previous user's data.
const CHANNEL = "cadre-auth";
// Identifies this tab, so a tab ignores its own announcements (it navigates by itself).
const TAB_ID = typeof crypto !== "undefined" ? crypto.randomUUID() : String(Math.random());

type AuthEvent = { type: "login" | "logout"; userId?: number };

export function announceAuthChange(event: AuthEvent) {
  try {
    const ch = new BroadcastChannel(CHANNEL);
    ch.postMessage({ ...event, source: TAB_ID });
    ch.close();
  } catch {
    /* BroadcastChannel unavailable: other tabs will catch up on focus */
  }
}

export function onAuthChange(handler: (event: AuthEvent) => void): () => void {
  try {
    const ch = new BroadcastChannel(CHANNEL);
    ch.onmessage = (e) => {
      const { source, ...event } = e.data as AuthEvent & { source?: string };
      if (source !== TAB_ID) handler(event);
    };
    return () => ch.close();
  } catch {
    return () => {};
  }
}
