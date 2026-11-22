export interface ComplaintHistory {
  event: string;
  from_status: string;
  to_status: string;
  actor_kind: string;
  details: string;
  occurred_at: string;
}

export type ComplaintStatus = "submitted" | "in_progress" | "resolved" | "rejected" | "closed";

export interface Complaint {
  reference: string;
  category: string;
  description: string;
  status: ComplaintStatus;
  priority: "low" | "medium" | "high" | "";
  assigned_to_user_id: number | null;
  sla_due_at: string | null;
  verification_required: boolean;
  submitted_at: string;
  resolved_at: string | null;
  closed_at: string | null;
  resolution_details: string;
  rejection_reason: string;
  history: ComplaintHistory[];
  feedback_submitted: boolean;
  reopening_status: "pending" | "approved" | "denied" | null;
}

export interface ComplaintAttachment {
  id: number;
  original_name: string;
  content_type: string;
  byte_size: number;
  uploaded_at: string;
}

export interface HandlerOption {
  user_id: number;
  display_name: string;
  kind: string;
  department: string;
}

export interface Announcement {
  id: number;
  title: string;
  body: string;
  published_at: string | null;
}
