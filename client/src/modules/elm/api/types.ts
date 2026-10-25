export interface LeaveCategory {
  id: number;
  code: string;
  name: string;
  description: string;
  annual_quota: string;
  carries_forward: boolean;
  continuous_counting: boolean;
  faculty_only: boolean;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  category: LeaveCategory;
  year: number;
  credited: string;
  consumed: string;
  balance: string;
}

export interface LeaveHistoryEntry {
  id: number;
  actor_id: number;
  action: string;
  from_status: string;
  to_status: string;
  remarks: string;
  created_at: string;
}

export interface LeaveApplicationItem {
  id: number;
  user_id: number;
  category_code: string;
  category_name: string;
  start_date: string;
  end_date: string;
  half_day: "none" | "first_half" | "second_half";
  days_count: string;
  status: string;
  station_leave: boolean;
  created_at: string;
}

export interface LeaveApplicationDetail extends LeaveApplicationItem {
  category: LeaveCategory;
  reason: string;
  station_address?: string;
  station_start_date?: string;
  station_end_date?: string;
  emergency_contact?: string;
  substitute_id?: number;
  substitute_status?: string;
  substitute_remarks?: string;
  substitute_acted_at?: string;
  unit_head_id?: number;
  unit_head_recommendation?: string;
  unit_head_remarks?: string;
  unit_head_acted_at?: string;
  sanctioning_authority_id?: number;
  sanction_remarks?: string;
  sanction_acted_at?: string;
  updated_at: string;
  history: LeaveHistoryEntry[];
}

export interface LeaveApplyPayload {
  category_code: string;
  start_date: string;
  end_date: string;
  reason: string;
  half_day?: "none" | "first_half" | "second_half";
  station_leave?: boolean;
  station_address?: string;
  station_start_date?: string;
  station_end_date?: string;
  emergency_contact?: string;
  substitute_id?: number | null;
}

export interface TransitionPayload {
  action: "approve" | "reject" | "recommend" | "not_recommend";
  remarks?: string;
}

export interface SubstitutePayload {
  action: "accept" | "decline";
  remarks?: string;
}

export interface WithdrawPayload {
  remarks?: string;
}
