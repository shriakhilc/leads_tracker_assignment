import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME } from "./lib/config";

// Guards internal routes (§6.2): unauthenticated users are redirected to /login.
export function middleware(req: NextRequest) {
  const token = req.cookies.get(COOKIE_NAME)?.value;
  if (!token) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("next", req.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/leads/:path*"],
};
