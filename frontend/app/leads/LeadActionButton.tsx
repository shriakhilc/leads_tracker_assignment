"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { LeadState } from "@/lib/types";

// Pending leads can be marked "reached out"; reached-out leads can be reverted back to
// pending to undo a mistaken click.
export default function LeadActionButton({
  leadId,
  state,
}: {
  leadId: string;
  state: LeadState;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const target: LeadState = state === "PENDING" ? "REACHED_OUT" : "PENDING";
  const label = state === "PENDING" ? "Mark reached out" : "Revert to pending";

  async function updateState() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/leads/${leadId}/state`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: target }),
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
      <button
        className={state === "PENDING" ? undefined : "secondary"}
        onClick={updateState}
        disabled={busy}
      >
        {busy ? "…" : label}
      </button>
      {error && (
        <span className="error" style={{ marginLeft: 8 }}>
          {error}
        </span>
      )}
    </div>
  );
}
