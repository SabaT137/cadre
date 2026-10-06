// Optimistic auth check: send visitors without a session cookie to /login.
// The FastAPI backend still verifies the token on every request.
import { NextResponse, type NextRequest } from "next/server";
import { TOKEN_COOKIE } from "@/lib/server";

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const hasSession = request.cookies.has(TOKEN_COOKIE);

  if (pathname.startsWith("/api/")) {
    if (!hasSession && pathname.startsWith("/api/backend/") && pathname !== "/api/backend/health") {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }
    return NextResponse.next();
  }
  if (pathname === "/login") {
    // Always reachable, even with a session, so people can switch accounts.
    return NextResponse.next();
  }
  if (!hasSession) {
    const url = new URL("/login", request.url);
    if (pathname !== "/") url.searchParams.set("next", pathname + search);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:png|svg|jpg|ico|webp)$).*)"],
};
