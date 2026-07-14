import { NextRequest, NextResponse } from "next/server";
import { API_INTERNAL_URL, COOKIE_NAME } from "@/lib/config";

// Proxies login to the backend and stores the JWT in an http-only cookie (§10: no JS-readable token).
export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  if (!body?.email || !body?.password) {
    return NextResponse.json({ detail: "Email and password are required" }, { status: 400 });
  }

  const res = await fetch(`${API_INTERNAL_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: body.email, password: body.password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Login failed" }));
    return NextResponse.json({ detail: err.detail ?? "Login failed" }, { status: res.status });
  }

  const { access_token } = await res.json();
  const response = NextResponse.json({ ok: true });
  response.cookies.set(COOKIE_NAME, access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 12,
  });
  return response;
}
