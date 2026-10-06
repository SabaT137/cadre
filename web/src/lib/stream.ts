"use client";

import { ApiError, goToLogin } from "./api";
import type { AgentName, Artifact, ChatRequest, PartInfo, Responder } from "./types";

export type StreamEvent =
  | { event: "thread"; data: { thread_id: string } }
  | { event: "route"; data: { agent: Responder; reason: string } }
  | { event: "message"; data: { agent: Responder; content: string; artifacts: Artifact[]; parts?: PartInfo[] } }
  | { event: "progress"; data: { type: "part" | "synthesis"; agent?: AgentName; status: "started" | "done" | "error"; task?: string } }
  | { event: "error"; data: { detail: string } }
  | { event: "done"; data: Record<string, never> };

/** POST /chat/stream and yield parsed SSE events. */
export async function* streamChat(req: ChatRequest, signal?: AbortSignal): AsyncGenerator<StreamEvent> {
  const res = await fetch("/api/backend/chat/stream", {
    method: "POST",
    headers: { "content-type": "application/json", accept: "text/event-stream" },
    body: JSON.stringify(req),
    signal,
  });
  if (res.status === 401) {
    goToLogin();
    throw new ApiError(401, "Your session has expired.");
  }
  if (!res.ok || !res.body) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(res.status, typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`);
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += value;
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const event = /^event: (.*)$/m.exec(chunk)?.[1];
      const raw = /^data: (.*)$/m.exec(chunk)?.[1];
      if (!event) continue;
      yield { event, data: raw ? JSON.parse(raw) : {} } as StreamEvent;
    }
  }
}
