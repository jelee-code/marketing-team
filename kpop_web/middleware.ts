import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const secret = process.env.SHARE_SECRET;

  // Dev/local: if no secret configured, allow access (skip the gate).
  if (!secret) return NextResponse.next();

  // Already authenticated via cookie — let through.
  const cookie = request.cookies.get("access")?.value;
  if (cookie === secret) return NextResponse.next();

  // First visit with ?k=<secret> — set cookie, strip query, redirect to clean URL.
  const queryKey = request.nextUrl.searchParams.get("k");
  if (queryKey === secret) {
    const url = request.nextUrl.clone();
    url.searchParams.delete("k");
    const response = NextResponse.redirect(url);
    response.cookies.set("access", secret, {
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 365, // 1 year
      path: "/",
    });
    return response;
  }

  // No valid auth — pretend the site doesn't exist.
  return new NextResponse(null, { status: 404 });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|robots.txt).*)"],
};
