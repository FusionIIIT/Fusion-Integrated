/** Wire types for the ELM API. */

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface LeaveCategory {
  code: string;
  label: string;
  annual_entitlement: number | null;
  carry_forward: boolean;
  continuous_day_counting: boolean;
  applicable_to: "F" | "S";
  supports_half_day: boolean;
}

export interface LeaveBalance {
  leave_category_code: string;
  category_label: string;
  entitlement_per_year: number;
  used_per_year: number;
  carried_forward_from_previous: number;
  year: number;
  available_days: number;
}

export interface LeaveApplication {
  pk: number;
  employee_user_id: number;
  leave_category_code: string;
  leave_category_label: string;
  requested_start: string; // ISO date string
  requested_end: string;   // ISO date string
  purpose_reason: string;
  station_leave: boolean;
  station_details: string;
  status: string;
  submitted_at: string;
  nominated_substitute_user_id: number | null;
  substitute_accepted: boolean | null;
  substitute_decline_reason: string;
}

export interface SubstituteNomination {
  pk: number;
  leave_application_pk: number;
  nominee_user_id: number;
  nominated_at: string;
  status: string;
  decline_reason: string;
}

export interface LeaveApplicationCreateRequest {
  leave_category_code: string;
  requested_start: string;
  requested_end: string;
  purpose_reason: string;
  station_leave: boolean;
  station_details?: string;
}

export interface LeaveApplicationCreateResponse {
  pk: number;
  status: string;
  message: string;
}

export interface LeaveBalancesResponse {
  balances: LeaveBalance[];
}

export interface LeaveHistoryEntry {
  type: "application" | "balance";
  pk?: number;
  leave_category_code: string;
  status?: string;
  requested_start?: string;
  requested_end?: string;
  purpose_reason?: string;
  submitted_at?: string;
  available_days?: number;
  entitlement?: number;
  used?: number;
  carry_forward?: number;
  year?: number;
}

export interface PrintApplicationRequest {
  application_pk: number;
}

export interface PrintApplicationResponse {
  application: LeaveApplication;
  print_data: Record<string, unknown>;
}

export interface SLAThresholdConfig {
  reminder_threshold_minutes: number;
  escalation_threshold_minutes: number;
  escalation_action: "notify" | "route_change" | "none";
}

export interface YearEndProcessingResult {
  year: number;
  transactions: Array<{
    user_id: number;
    category: string;
    action: string;
    days?: number;
    converted_el?: number;
  }>;
  summary: {
    total_transactions: number;
    categories_processed: number;
  };
}