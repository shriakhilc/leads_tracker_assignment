import { NextRequest, NextResponse } from "next/server";
import { API_INTERNAL_URL, COOKIE_NAME } from "@/lib/config";

// Proxies the state transition to the backend, forwarding the http-only JWT.
export async function PATCH(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const token = req.cookies.get(COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }
  const body = await req.json().catch(() => ({}));

  const res = await fetch(`${API_INTERNAL_URL}/leads/${params.id}/state`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });

  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
