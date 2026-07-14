"use client";

import { useRouter, useSearchParams } from "next/navigation";

const PAGE_SIZES = [25, 50, 100];

export default function Pagination({
  page,
  pageSize,
  total,
}: {
  page: number;
  pageSize: number;
  total: number;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  function go(overrides: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(overrides)) {
      if (value === null) params.delete(key);
      else params.set(key, value);
    }
    const qs = params.toString();
    router.push(qs ? `/leads?${qs}` : "/leads");
  }

  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);

  return (
    <div className="pagination">
      <div className="page-size">
        <label htmlFor="page_size" style={{ marginBottom: 0 }}>
          Rows per page
        </label>
        <select
          id="page_size"
          value={pageSize}
          onChange={(e) => go({ page_size: e.target.value, page: null })}
          style={{ width: "auto" }}
        >
          {PAGE_SIZES.map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
      </div>

      <div className="page-nav">
        <span className="muted">
          {first}-{last} of {total}
        </span>
        <button
          className="secondary"
          disabled={page <= 1}
          onClick={() => go({ page: String(page - 1) })}
        >
          Previous
        </button>
        <span className="muted">
          Page {page} of {totalPages}
        </span>
        <button
          className="secondary"
          disabled={page >= totalPages}
          onClick={() => go({ page: String(page + 1) })}
        >
          Next
        </button>
      </div>
    </div>
  );
}
