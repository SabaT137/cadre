"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";
import type { Department } from "@/lib/types";
import { newThreadId, setPendingPrompt } from "@/lib/utils";

/** Open a new conversation, optionally sending a first message. */
export function useStartChat() {
  const router = useRouter();
  return useCallback((message: string, department: Department = "auto") => {
    const id = newThreadId();
    setPendingPrompt(id, { message, department });
    router.push(`/chat/${id}`);
  }, [router]);
}
