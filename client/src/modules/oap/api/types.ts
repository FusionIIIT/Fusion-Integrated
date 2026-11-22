/** Wire types for Other Academic Procedures API.
 * Matches openapi/fusion-integrated.v1.yaml field by field.
 */

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
  count?: number;
}

export type LeaveTypeEnum = "CASUAL" | "MEDICAL" | "SHORT" | "SEMESTER_LEAVE";

export type RequestStatusEnum =
  | "PENDING"
  | "RECOMMENDED"
  | "APPROVED"
  | "REJECTED"
  | "CANCELLED";

export interface StudentLeaveRequest {
  id: number;
  student_id: string;
  student_name: string;
  leave_type: LeaveTypeEnum;
  start_date: string;
  end_date: string;
  duration_days: number;
  reason: string;
  status: RequestStatusEnum;
  supervisor_id?: string;
  supervisor_remarks?: string;
  hod_id?: string;
  hod_remarks?: string;
  document_url?: string;
  created_at: string;
  updated_at: string;
}

export type PurposeEnum =
  | "BANK_LOAN"
  | "PASSPORT"
  | "VISA"
  | "INTERNSHIP"
  | "GENERAL";

export type BonafideRequestStatusEnum = "PENDING" | "APPROVED" | "REJECTED";

export interface BonafideRequest {
  id: number;
  student_id: string;
  purpose: PurposeEnum;
  details?: string | null;
  status: BonafideRequestStatusEnum;
  certificate_number?: string | null;
  issued_at?: string | null;
  issued_by?: string;
  rejection_reason?: string;
  created_at: string;
}

export type ReasonEnum = "GRADUATION" | "WITHDRAWAL" | "MIGRATION";

export type OverallStatusEnum = "PENDING" | "CLEARED" | "REJECTED";

export type DepartmentEnum =
  | "LIBRARY"
  | "HOSTEL"
  | "ACCOUNTS"
  | "SPORTS"
  | "LABORATORY"
  | "DISCIPLINE";

export type SignoffStatusEnum = "PENDING" | "CLEARED" | "DUES_PENDING";

export interface NoDuesDepartmentalSignoff {
  id: number;
  department: DepartmentEnum;
  status: SignoffStatusEnum;
  dues_amount: string;
  remarks?: string;
  signoff_by?: string;
  signoff_at?: string | null;
}

export interface NoDuesRequest {
  id: number;
  student_id: string;
  reason: ReasonEnum;
  overall_status: OverallStatusEnum;
  clearance_certificate_number?: string | null;
  completed_at?: string | null;
  finalized_by?: string;
  signoffs: NoDuesDepartmentalSignoff[];
  created_at: string;
}

export type BranchChangeStatusEnum =
  | "SUBMITTED"
  | "VERIFIED_ELIGIBLE"
  | "INELIGIBLE"
  | "ALLOCATED"
  | "APPROVED"
  | "REJECTED";

export interface BranchChangeRequest {
  id: number;
  student_id: string;
  current_branch: string;
  preferred_branch_1: string;
  preferred_branch_2?: string | null;
  current_cpi: string;
  credits_completed: number;
  has_backlogs: boolean;
  status: BranchChangeStatusEnum;
  allocated_branch?: string;
  approved_by?: string;
  remarks?: string;
  created_at: string;
}
