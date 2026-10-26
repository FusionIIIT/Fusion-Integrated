export interface LeaveApplication {
  id: number;
  user_id: number;
  leave_category: string;
  leave_category_display: string;
  start_date: string;
  end_date: string;
  chargeable_days: string;
  reason: string;
  half_day: boolean;
  half_day_type: string;
  station_leave: boolean;
  station_start_date?: string | null;
  station_end_date?: string | null;
  station_address: string;
  station_emergency_contact: string;
  substitute_required: boolean;
  substitute_id?: number | null;
  substitute_status: string;
  substitute_remarks: string;
  status: string;
  status_display: string;
  unit_head_id?: number | null;
  unit_head_recommendation: string;
  unit_head_remarks: string;
  unit_head_acted_at?: string | null;
  sanctioning_authority_id?: number | null;
  sanction_role: string;
  sanction_decision: string;
  sanction_remarks: string;
  sanction_acted_at?: string | null;
  original_application_id?: number | null;
  resumption_date?: string | null;
  resumption_reason: string;
  resumption_status: string;
  created_at: string;
  updated_at: string;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  year: number;
  leave_category: string;
  category_display: string;
  credited: string;
  used: string;
  available: string;
}
