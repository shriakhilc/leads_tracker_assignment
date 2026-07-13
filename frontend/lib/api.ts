// Server-side API client for the FastAPI backend. Never imported by client components.
import "server-only";
import { API_INTERNAL_URL } from "./config";
import { getToken } from "./session";
import type { CurrentUser, LeadList } from "./types";

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function getCurrentUser(): Promise<CurrentUser | null> {
  const res = await fetch(`${API_INTERNAL_URL}/auth/me`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) return null;
  return res.json();
}

export async function listLeads(params: {
  state?: string;
  assignedToMe?: boolean;
}): Promise<LeadList> {
  const query = new URLSearchParams();
  if (params.state) query.set("state", params.state);
  if (params.assignedToMe) query.set("assigned_to_me", "true");
  query.set("limit", "200");

  const res = await fetch(`${API_INTERNAL_URL}/leads?${query.toString()}`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to load leads (${res.status})`);
  }
  return res.json();
}
