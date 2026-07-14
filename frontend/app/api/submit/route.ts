import { NextRequest, NextResponse } from "next/server";
import { API_INTERNAL_URL } from "@/lib/config";

// Public lead submission. Proxies the multipart form to the backend (same-origin → no CORS).
export async function POST(req: NextRequest) {
  const formData = await req.formData();

  const res = await fetch(`${API_INTERNAL_URL}/leads`, {
    method: "POST",
    body: formData,
  });

  const data = await res.json().catch(() => ({ detail: "Submission failed" }));
  return NextResponse.json(data, { status: res.status });
}

// Next.js: allow larger request bodies for the resume upload.
export const runtime = "nodejs";
