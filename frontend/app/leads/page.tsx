import { listLeads, getCurrentUser } from "@/lib/api";
import Filters from "./Filters";
import LogoutButton from "./LogoutButton";
import MarkReachedOutButton from "./MarkReachedOutButton";

export const dynamic = "force-dynamic";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

export default async function LeadsDashboard({
  searchParams,
}: {
  searchParams: { state?: string; assigned_to_me?: string };
}) {
  const user = await getCurrentUser();
  const stateFilter =
    searchParams.state === "PENDING" || searchParams.state === "REACHED_OUT"
      ? searchParams.state
      : undefined;
  const assignedToMe = searchParams.assigned_to_me === "true";

  const { items, total } = await listLeads({ state: stateFilter, assignedToMe });

  return (
    <div className="container">
      <div className="topbar">
        <div>
          <h1>Leads</h1>
          <p className="muted">
            Signed in as {user?.email ?? "unknown"} · {total} lead{total === 1 ? "" : "s"}
          </p>
        </div>
        <LogoutButton />
      </div>

      <Filters state={stateFilter} assignedToMe={assignedToMe} />

      {items.length === 0 ? (
        <div className="card">
          <p className="muted" style={{ margin: 0 }}>
            No leads match the current filters.
          </p>
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>State</th>
                <th>Assigned to</th>
                <th>Submitted</th>
                <th>Resume</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((lead) => (
                <tr key={lead.id}>
                  <td>
                    {lead.first_name} {lead.last_name}
                  </td>
                  <td>{lead.email}</td>
                  <td>
                    <span className={`badge ${lead.state.toLowerCase()}`}>
                      {lead.state === "REACHED_OUT" ? "Reached out" : "Pending"}
                    </span>
                  </td>
                  <td>{lead.assignee?.email ?? "—"}</td>
                  <td className="muted">{formatDate(lead.created_at)}</td>
                  <td>
                    <a href={`/api/leads/${lead.id}/resume`} target="_blank" rel="noreferrer">
                      Download
                    </a>
                  </td>
                  <td>
                    {lead.state === "PENDING" ? (
                      <MarkReachedOutButton leadId={lead.id} />
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
