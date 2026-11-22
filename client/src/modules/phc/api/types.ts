/** Money arrives as a STRING: parsing it into a JS number loses precision. */

export interface Page<T> {
  results: T[];
}

export interface DoctorSchedule {
  id: number;
  doctor_name: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_published: boolean;
  published_at: string | null;
  published_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface DoctorScheduleCreate {
  doctor_name: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
}

export interface DoctorScheduleUpdate {
  day_of_week?: number;
  start_time?: string;
  end_time?: string;
}

export interface DoctorAttendance {
  id: number;
  doctor_name: string;
  date: string;
  status: "available" | "departed";
  updated_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface DoctorAttendanceMark {
  doctor_name: string;
  date: string;
  status: "available" | "departed";
}

export interface ScheduleResponse {
  schedules: DoctorSchedule[];
  attendance: Record<string, "available" | "departed">;
}

export interface Patient {
  user_id: number;
  display_name: string;
  kind: string;
}

export interface Visit {
  id: number;
  patient: number;
  recorded_by: number | null;
  notes: string;
  visit_date: string;
}

export interface VisitCreate {
  patient_id: number;
  notes?: string;
}

export interface Prescription {
  id: number;
  visit: number;
  patient: number;
  medicine: string;
  dosage: string;
  recorded_by: number | null;
  created_at: string;
}

export interface PrescriptionCreate {
  visit_id: number;
  patient_id: number;
  medicine: string;
  dosage?: string;
}

export type ClaimState =
  | "submitted" | "pending_audit" | "pending_sanction"
  | "approved_for_payment" | "reimbursed" | "rejected";

export interface ReimbursementClaim {
  claim_id: number;
  employee: number;
  prescription: number;
  expense_date: string;
  amount: string;
  description: string;
  state: ClaimState;
  stage_actor: string;
  action_history: string[];
  created_at: string;
  updated_at: string;
}

export interface ReimbursementClaimCreate {
  prescription_id: number;
  expense_date: string;
  amount: string;
  description?: string;
}

export interface ClaimTransition {
  note?: string;
}

export interface ClaimDecision {
  decision: "approve" | "reject";
  note?: string;
}

export interface InventoryItem {
  id: number;
  name: string;
  unit: string;
  quantity: number;
  reorder_threshold: number;
  created_at: string;
  updated_at: string;
}

export interface InventoryItemCreate {
  name: string;
  unit?: string;
  reorder_threshold?: number;
}

export interface StockAdjustment {
  id: number;
  item: number;
  quantity: number;
  direction: "add" | "deduct";
  adjusted_by: number | null;
  reason: string;
  created_at: string;
}

export interface StockAdjustmentCreate {
  item_id: number;
  quantity: number;
  direction: "add" | "deduct";
  reason?: string;
}

export type RequisitionState =
  | "pending_approval" | "approved" | "rejected" | "fulfilled";

export interface Requisition {
  requisition_id: number;
  originator: number;
  decided_by: number | null;
  decided_at: string | null;
  state: RequisitionState;
  decision_note: string;
  created_at: string;
  updated_at: string;
}

export interface RequisitionItem {
  id: number;
  requisition: number;
  item: number;
  quantity: number;
  created_at: string;
  updated_at: string;
}

export interface RequisitionItemInput {
  item_id: number;
  quantity: number;
}

export interface RequisitionCreate {
  items: RequisitionItemInput[];
}

export interface RequisitionDecision {
  decision: "approve" | "reject";
  note?: string;
}

export interface AmbulanceLog {
  id: number;
  timestamp: string;
  patient_name: string;
  destination: string;
  logged_by: number | null;
  created_at: string;
}

export interface AmbulanceLogCreate {
  timestamp: string;
  patient_name: string;
  destination: string;
}

export interface HealthAdvisory {
  id: number;
  title: string;
  content: string;
  is_published: boolean;
  published_at: string | null;
  published_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface HealthAdvisoryCreate {
  title: string;
  content: string;
}

export interface AuditLog {
  id: number;
  actor: number | null;
  actor_role: string;
  action: string;
  target_type: string;
  target_id: number;
  detail: Record<string, unknown>;
  created_at: string;
}

export type ReportCategory = "demographics" | "utilization" | "inventory";

export interface AdminReport {
  category: string;
  error?: string;
  note?: string;
  patient_count_by_kind?: Record<string, number>;
  visits?: number;
  prescriptions?: number;
  ambulance_logs?: number;
  claims?: number;
  requisitions?: number;
  stock_adjustments?: number;
  items?: number;
  low_stock_items?: string[];
}
