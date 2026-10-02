// Backend-for-frontend proxy: forwards /api/backend/* to FastAPI with the JWT from the httpOnly cookie.
// Streams responses through unchanged, so SSE (/chat/stream) and file downloads work.
import { NextResponse, type NextRequest } from "next/server";
import { BACKEND_URL, TOKEN_COOKIE } from "@/lib/server";

export const dynamic = "force-dynamic";

const PASS_RESPONSE_HEADERS = ["content-type", "content-disposition", "content-length", "cache-control"];

async function handler(req: NextRequest, ctx: RouteContext<"/api/backend/[...path]">) {
  const { path } = await ctx.params;
  if (path[0] === "auth" && path[1] === "login") {
    return NextResponse.json({ detail: "Use /api/auth/login" }, { status: 400 });
  }
  const url = `${BACKEND_URL}/${path.map(encodeURIComponent).join("/")}${req.nextUrl.search}`;
  const headers = new Headers({ accept: req.headers.get("accept") ?? "*/*" });
  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const token = req.cookies.get(TOKEN_COOKIE)?.value;
  if (token) headers.set("authorization", `Bearer ${token}`);

  const init: RequestInit = { method: req.method, headers, cache: "no-store", redirect: "manual" };
  if (req.method !== "GET" && req.method !== "HEAD") init.body = await req.arrayBuffer();

  let upstream: Response;
  try {
    upstream = await fetch(url, init);
  } catch {
    return NextResponse.json({ detail: "The assistant service is unreachable." }, { status: 503 });
  }

  const resHeaders = new Headers();
  for (const h of PASS_RESPONSE_HEADERS) {
    const v = upstream.headers.get(h);
    if (v) resHeaders.set(h, v);
  }
  if (upstream.headers.get("content-type")?.includes("text/event-stream")) {
    resHeaders.set("cache-control", "no-cache, no-transform");
    resHeaders.set("x-accel-buffering", "no");
    resHeaders.delete("content-length");
  }
  const res = new NextResponse(upstream.body, { status: upstream.status, headers: resHeaders });
  if (upstream.status === 401) res.cookies.delete(TOKEN_COOKIE);
  return res;
}

export { handler as GET, handler as POST, handler as PATCH, handler as PUT, handler as DELETE };
