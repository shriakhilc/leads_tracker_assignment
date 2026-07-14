import Link from "next/link";
import { listLeads, getCurrentUser } from "@/lib/api";
import Filters from "./Filters";
import LogoutButton from "./LogoutButton";
import LeadActionButton from "./LeadActionButton";
import Pagination from "./Pagination";

export const dynamic = "force-dynamic";

const PAGE_SIZES = [25, 50, 100];
const DEFAULT_PAGE_SIZE = 25;

type SortKey = "name" | "email" | "state" | "assignee" | "created_at";

// Every column except Resume and Action is sortable; the key is what the API expects.
const SORT_COLUMNS: { key: SortKey; label: string }[] = [
  { key: "name", label: "Name" },
  { key: "email", label: "Email" },
  { key: "state", label: "State" },
  { key: "assignee", label: "Assigned to" },
  { key: "created_at", label: "Submitted" },
];
const SORT_KEYS = SORT_COLUMNS.map((c) => c.key as string);

// Render every timestamp in UTC with an explicit timezone abbreviation (e.g. "Jul 13, 2026, 14:30 UTC").
function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    // Force h23 (00-23). `hour12: false` alone can resolve to the h24 cycle in some
    // engines, rendering midnight as "24:31" instead of "00:31".
    hourCycle: "h23",
    timeZone: "UTC",
    timeZoneName: "short",
  }).format(new Date(iso));
}

export default async function LeadsDashboard({
  searchParams,
}: {
  searchParams: {
    state?: string;
    assigned_to_me?: string;
    sort?: string;
    order?: string;
    page?: string;
    page_size?: string;
  };
}) {
  const user = await getCurrentUser();

  const stateFilter =
    searchParams.state === "PENDING" || searchParams.state === "REACHED_OUT"
      ? searchParams.state
      : undefined;
  const assignedToMe = searchParams.assigned_to_me === "true";

  const sort = (SORT_KEYS.includes(searchParams.sort ?? "")
    ? searchParams.sort
    : "created_at") as SortKey;
  const order = searchParams.order === "asc" ? "asc" : "desc";

  const pageSize = PAGE_SIZES.includes(Number(searchParams.page_size))
    ? Number(searchParams.page_size)
    : DEFAULT_PAGE_SIZE;
  const requestedPage = Number(searchParams.page);
  const page = Number.isInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;

  const { items, total } = await listLeads({
    state: stateFilter,
    assignedToMe,
    sort,
    order,
    limit: pageSize,
    offset: (page - 1) * pageSize,
  });

  // A sortable header links to the same view sorted by its column; clicking the active
  // column flips direction. Filters and page size are preserved; the page resets to 1.
  function sortHref(key: SortKey): string {
    const params = new URLSearchParams();
    if (stateFilter) params.set("state", stateFilter);
    if (assignedToMe) params.set("assigned_to_me", "true");
    params.set("sort", key);
    params.set("order", sort === key && order === "asc" ? "desc" : "asc");
    params.set("page_size", String(pageSize));
    return `/leads?${params.toString()}`;
  }

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

      {total === 0 ? (
        <div className="card">
          <p className="muted" style={{ margin: 0 }}>
            No leads match the current filters.
          </p>
        </div>
      ) : (
        <>
          {items.length === 0 ? (
            <div className="card">
              <p className="muted" style={{ margin: 0 }}>
                No leads on this page.
              </p>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table>
                <thead>
                  <tr>
                    {SORT_COLUMNS.map((col) => {
                      const active = sort === col.key;
                      return (
                        <th
                          key={col.key}
                          className={col.key === "state" ? "col-state" : undefined}
                          aria-sort={active ? (order === "asc" ? "ascending" : "descending") : "none"}
                        >
                          <Link href={sortHref(col.key)} className="sort-header">
                            {col.label}
                            <span className="sort-indicator">
                              {active ? (order === "asc" ? "▲" : "▼") : ""}
                            </span>
                          </Link>
                        </th>
                      );
                    })}
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
                      <td className="col-state">
                        <span className={`badge ${lead.state.toLowerCase()}`}>
                          {lead.state === "REACHED_OUT" ? "Reached out" : "Pending"}
                        </span>
                      </td>
                      <td>{lead.assignee?.email ?? "-"}</td>
                      <td className="muted">{formatDate(lead.created_at)}</td>
                      <td>
                        <a href={`/api/leads/${lead.id}/resume`} target="_blank" rel="noreferrer">
                          Download
                        </a>
                      </td>
                      <td>
                        <LeadActionButton leadId={lead.id} state={lead.state} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <Pagination page={page} pageSize={pageSize} total={total} />
        </>
      )}
    </div>
  );
}
