/** TypeScript interfaces for the Complaint Management System (CMS). */

export type ComplaintStatus = "submitted" | "in_progress" | "resolved" | "rejected" | "closed";
export type ComplaintPriority = "low" | "medium" | "high";
export type EscalationType = "none" | "manual" | "automatic_sla";
export type ClosureVerification = "none" | "user" | "supervisor";
export type ReopeningStatus = "none" | "pending" | "approved" | "denied";

export interface ComplaintCategory {
  id: number;
  name: string;
  description: string;
  default_sla_hours: number;
  is_active: boolean;
}

export interface ComplaintAttachment {
  id: number;
  file: string;
  file_name: string;
  file_size: number;
  uploaded_by_user_id: number;
  created_at: string;
}

export interface ComplaintTransition {
  id: number;
  from_status: string;
  to_status: string;
  actor_user_id: number | null;
  actor_role: string;
  remarks: string;
  created_at: string;
}

export interface ComplaintFeedback {
  id: number;
  rating: number;
  comments: string;
  created_at: string;
}

export interface ComplaintListItem {
  id: number;
  complaint_id: string;
  complainant_user_id: number;
  category_id: number;
  category_name: string;
  location: string;
  description: string;
  status: ComplaintStatus;
  priority: ComplaintPriority;
  assigned_worker_name: string;
  is_escalated: boolean;
  verification_required: ClosureVerification;
  reopening_status: ReopeningStatus;
  sla_deadline: string | null;
  created_at: string;
  resolved_at: string | null;
  closed_at: string | null;
}

export interface ComplaintDetail extends ComplaintListItem {
  category: ComplaintCategory;
  assigned_worker_id: number | null;
  resolution_details: string;
  rejection_reason: string;
  escalation_type: EscalationType;
  escalated_at: string | null;
  escalation_remarks: string;
  rejected_at: string | null;
  reopening_reason: string;
  reopening_review_remarks: string;
  sla_reminder_sent: boolean;
  attachments: ComplaintAttachment[];
  transitions: ComplaintTransition[];
  feedback: ComplaintFeedback | null;
  updated_at: string;
}

export interface ComplaintAnnouncement {
  id: number;
  title: string;
  content: string;
  category_id: number | null;
  category_name?: string;
  author_user_id: number;
  author_name: string;
  is_active: boolean;
  pinned: boolean;
  created_at: string;
}

export interface CategorySummaryCount {
  id: number;
  name: string;
  count: number;
}

export interface ReportsSummary {
  total_complaints: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  by_category: CategorySummaryCount[];
  escalated_count: number;
  sla_breached_count: number;
  average_rating: number;
  total_feedback: number;
}

export interface CmsRoleAssignment {
  id: number;
  role_type: "handler" | "supervisor";
  role_type_label: string;
  user_id: number;
  assigned_by_user_id: number;
  start_date: string;
  end_date: string;
  is_active: boolean;
  created_at: string;
}

export interface ActiveCmsRoles {
  active_handler: CmsRoleAssignment | null;
  active_supervisor: CmsRoleAssignment | null;
}

export interface SlaCheckResult {
  escalated_count: number;
  reminders_sent: number;
}

// Request payloads
export interface SubmitComplaintPayload {
  category_id: number;
  location: string;
  description: string;
  priority?: ComplaintPriority;
  verification_required?: ClosureVerification;
  attachments?: File[];
}

export interface AssignComplaintPayload {
  worker_id?: number | null;
  worker_name?: string;
  priority?: ComplaintPriority;
  category_id?: number;
  remarks?: string;
}

export interface UpdateProgressPayload {
  progress_notes: string;
}

export interface ResolveComplaintPayload {
  resolution_details: string;
}

export interface RejectComplaintPayload {
  rejection_reason: string;
}

export interface VerifyClosePayload {
  remarks?: string;
}

export interface ReopeningRequestPayload {
  reopening_reason: string;
}

export interface ReopeningReviewPayload {
  approved: boolean;
  review_remarks?: string;
}

export interface ManualEscalatePayload {
  remarks: string;
}

export interface SubmitFeedbackPayload {
  rating: number;
  comments?: string;
}

export interface PublishAnnouncementPayload {
  title: string;
  content: string;
  category_id?: number | null;
  pinned?: boolean;
}

export interface AssignRolePayload {
  role_type: "handler" | "supervisor";
  user_id: number;
  start_date: string;
  end_date: string;
}
