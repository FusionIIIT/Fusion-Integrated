export interface CmsPage<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface CmsConfig {
  attachment_max_bytes: number;
  attachment_max_count: number;
  attachment_allowed_extensions: string[];
}

export type CmsStatus = "submitted" | "in_progress" | "resolved" | "rejected" | "closed";
export type CmsPriority = "low" | "medium" | "high";

export interface CmsAttachment {
  id: number;
  file_name: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
  download_url: string;
}

export interface CmsHistory {
  from_status: string;
  to_status: CmsStatus;
  actor_user_id: number | null;
  actor_role: string;
  note: string;
  created_at: string;
}

export interface CmsProgress {
  id: number;
  actor_user_id: number;
  update_text: string;
  created_at: string;
}

export interface CmsComplaint {
  id: number;
  complaint_id: string;
  complainant_user_id: number;
  category: string;
  description: string;
  status: CmsStatus;
  priority: CmsPriority | "";
  assigned_handler_user_id: number | null;
  assignment_note: string;
  resolution_details: string;
  rejection_reason: string;
  closure_verifier: "complainant" | "supervisor" | "";
  closed_at: string | null;
  reopened_at: string | null;
  sla_due_at: string | null;
  escalated: boolean;
  escalated_at: string | null;
  escalation_kind: "manual" | "automatic" | "";
  attachments: CmsAttachment[];
  history: CmsHistory[];
  progress_updates: CmsProgress[];
  created_at: string;
  updated_at: string;
}

export interface CmsReopeningRequest {
  id: number;
  complaint: number;
  requested_by_user_id: number;
  request_reason: string;
  decision: "pending" | "approved" | "denied";
  decided_by_user_id: number | null;
  decision_note: string;
  created_at: string;
  decided_at: string | null;
}

export interface CmsFeedback {
  id: number;
  complaint: number;
  submitted_by_user_id: number;
  feedback_text: string;
  created_at: string;
}

export interface CmsAnnouncement {
  id: number;
  title: string;
  body: string;
  published_by_user_id: number;
  notify_users: boolean;
  published_at: string;
}

export interface CmsRoleAssignment {
  id: number;
  role: "handler" | "supervisor";
  user_id: number;
  starts_at: string;
  ends_at: string;
  is_active: boolean;
  created_at: string;
  assigned_by_user_id: number;
}

export interface CmsReport {
  total: number;
  by_status: { status: CmsStatus; count: number }[];
  by_priority: { priority: CmsPriority | ""; count: number }[];
  by_category: { category: string; count: number }[];
  escalated: number;
  unresolved: number;
  oldest_unresolved_at: string | null;
}
