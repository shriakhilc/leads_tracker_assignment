"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function MarkReachedOutButton({ leadId }: { leadId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function markReachedOut() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/leads/${leadId}/state`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: "REACHED_OUT" }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? "Failed");
        return;
      }
      router.refresh();
    } catch {
      setError("Network error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <button onClick={markReachedOut} disabled={busy}>
        {busy ? "…" : "Mark reached out"}
      </button>
      {error && <span className="error" style={{ marginLeft: 8 }}>{error}</span>}
    </div>
  );
}
