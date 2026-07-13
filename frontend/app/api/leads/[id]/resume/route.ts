import { NextRequest, NextResponse } from "next/server";
import { API_INTERNAL_URL, COOKIE_NAME } from "@/lib/config";

// Streams the resume through the app so the browser never needs the JWT or a
// MinIO-internal hostname — the app proxies the authenticated backend download.
export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const token = req.cookies.get(COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const res = await fetch(`${API_INTERNAL_URL}/leads/${params.id}/resume`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok || !res.body) {
    return NextResponse.json({ detail: "Resume not available" }, { status: res.status });
  }

  const headers = new Headers();
  headers.set(
    "Content-Type",
    res.headers.get("Content-Type") ?? "application/octet-stream"
  );
  const disposition = res.headers.get("Content-Disposition");
  if (disposition) headers.set("Content-Disposition", disposition);

  return new NextResponse(res.body, { status: 200, headers });
}
