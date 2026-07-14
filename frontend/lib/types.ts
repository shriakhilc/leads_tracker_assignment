export type LeadState = "PENDING" | "REACHED_OUT";

export interface Assignee {
  attorney_id: string;
  email: string;
  full_name: string;
}

export interface Lead {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  resume_filename: string;
  resume_content_type: string;
  state: LeadState;
  created_at: string;
  updated_at: string;
  assignee: Assignee | null;
}

export interface LeadList {
  items: Lead[];
  total: number;
  limit: number;
  offset: number;
}

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
}
