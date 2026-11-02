export interface OAPAuditTrail {
  id: number;
  procedure_type: string;
  record_id: number;
  action: string;
  actor_user_id: number;
  actor_role: string;
  previous_state?: string;
  new_state: string;
  remarks?: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface StudentLeave {
  id: number;
  user_id: number;
  department: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  chargeable_days: number;
  medical_certificate_attached: boolean;
  reason: string;
  document_reference?: string;
  status: 'SUBMITTED' | 'APPROVED' | 'REJECTED';
  hod_user_id?: number;
  hod_remarks?: string;
  decided_at?: string;
  created_at: string;
}

export interface BonafideRequest {
  id: number;
  user_id: number;
  purpose: string;
  certificate_type: string;
  status: 'SUBMITTED' | 'APPROVED' | 'REJECTED';
  academic_admin_user_id?: number;
  admin_remarks?: string;
  decided_at?: string;
  certificate_number?: string;
  verification_hash?: string;
  issue_date?: string;
  valid_until?: string;
  is_expired: boolean;
  created_at: string;
}

export interface NoDuesAuthorityClearance {
  id: number;
  domain: 'LIBRARY' | 'HOSTEL' | 'MESS' | 'DEPARTMENT' | 'LAB' | 'ACADEMIC_SECTION' | 'STUDENT_SECTION';
  status: 'PENDING' | 'CLEARED' | 'DUES_OUTSTANDING';
  dues_amount: number;
  fine_details?: string;
  receipt_reference?: string;
  remarks?: string;
  verifier_user_id?: number;
  verified_at?: string;
}

export interface NoDuesRequest {
  id: number;
  user_id: number;
  program: 'UG' | 'PG';
  department: string;
  status: 'VERIFICATION_IN_PROGRESS' | 'VERIFICATION_COMPLETE_ALL_CLEAR' | 'VERIFICATION_COMPLETE_DUES_PENDING' | 'FINALIZED' | 'REJECTED';
  all_domains_cleared: boolean;
  finalized_by_user_id?: number;
  finalized_at?: string;
  certificate_number?: string;
  verification_hash?: string;
  finalization_remarks?: string;
  clearances?: NoDuesAuthorityClearance[];
  created_at: string;
}

export interface ThesisSupervisorAssignment {
  id: number;
  student_user_id: number;
  faculty_user_id: number;
  department: string;
  academic_year: string;
  assigned_by_user_id: number;
  is_active: boolean;
  created_at: string;
}

export interface TAAssignment {
  id: number;
  student_user_id: number;
  faculty_user_id?: number;
  course_code?: string;
  course_name?: string;
  department: string;
  semester: string;
  academic_year: string;
  assigned_by_user_id: number;
  is_active: boolean;
  created_at: string;
}

export interface AssistantshipClaim {
  id: number;
  user_id: number;
  month: number;
  year: number;
  stipend_amount: number;
  attendance_percentage: number;
  pro_rata_stipend: number;
  funding_source: string;
  work_summary: string;
  hours_worked: number;
  thesis_supervisor_user_id: number;
  ta_supervisor_user_id: number;
  thesis_supervisor_verified: boolean;
  thesis_supervisor_role_verified: boolean;
  ta_supervisor_verified: boolean;
  ta_supervisor_role_verified: boolean;
  dept_admin_reviewed: boolean;
  status: string;
  hod_user_id?: number;
  hod_remarks?: string;
  disbursed_by_user_id?: number;
  disbursement_reference?: string;
  disbursed_at?: string;
  created_at: string;
}

export interface GraduateSeminarRequest {
  id: number;
  user_id: number;
  topic: string;
  abstract: string;
  preferred_date: string;
  status: 'AWAITING_SCHEDULING' | 'SCHEDULED' | 'COMPLETED';
  scheduled_date?: string;
  scheduled_time?: string;
  venue?: string;
  evaluation_result?: 'SATISFACTORY' | 'UNSATISFACTORY';
  history_log?: Array<Record<string, any>>;
  created_at: string;
}

export interface OAPNotification {
  id: number;
  recipient_user_id: number;
  notification_type: 'ALERT' | 'EMAIL';
  event_type: string;
  message: string;
  is_read: boolean;
  created_at: string;
}
