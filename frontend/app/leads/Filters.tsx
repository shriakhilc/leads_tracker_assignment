"use client";

import { useRouter } from "next/navigation";

export default function Filters({
  state,
  assignedToMe,
}: {
  state?: string;
  assignedToMe: boolean;
}) {
  const router = useRouter();

  function apply(nextState: string | undefined, nextAssigned: boolean) {
    const params = new URLSearchParams();
    if (nextState) params.set("state", nextState);
    if (nextAssigned) params.set("assigned_to_me", "true");
    const qs = params.toString();
    router.push(qs ? `/leads?${qs}` : "/leads");
  }

  return (
    <div className="toolbar">
      <div>
        <label htmlFor="state" style={{ display: "inline", marginRight: 8 }}>
          State
        </label>
        <select
          id="state"
          value={state ?? ""}
          onChange={(e) => apply(e.target.value || undefined, assignedToMe)}
          style={{ width: "auto", display: "inline-block" }}
        >
          <option value="">All</option>
          <option value="PENDING">Pending</option>
          <option value="REACHED_OUT">Reached out</option>
        </select>
      </div>

      <div className="checkbox-row">
        <input
          id="assigned"
          type="checkbox"
          checked={assignedToMe}
          onChange={(e) => apply(state, e.target.checked)}
        />
        <label htmlFor="assigned" style={{ marginBottom: 0 }}>
          Assigned to me
        </label>
      </div>
    </div>
  );
}
