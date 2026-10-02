import { NextResponse, type NextRequest } from "next/server";
import { BACKEND_URL, TOKEN_COOKIE, TOKEN_MAX_AGE } from "@/lib/server";

export async function POST(req: NextRequest) {
  let body: { username?: string; password?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "Invalid request" }, { status: 400 });
  }
  let upstream: Response;
  try {
    upstream = await fetch(`${BACKEND_URL}/auth/login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ username: body.username ?? "", password: body.password ?? "" }),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ detail: "The assistant service is unreachable. Please try again." }, { status: 503 });
  }
  const data = await upstream.json().catch(() => ({}));
  if (!upstream.ok) {
    return NextResponse.json({ detail: data.detail ?? "Login failed" }, { status: upstream.status });
  }
  const res = NextResponse.json({ user: data.user });
  res.cookies.set(TOKEN_COOKIE, data.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: TOKEN_MAX_AGE,
  });
  return res;
}
