export interface LeaveBalance {
  id: number;
  user_id: number;
  year: number;
  leave_type: "CL" | "RH" | "SCL" | "EL" | "VL" | "COL";
  allocated: string | number;
  availed: string | number;
  pending: string | number;
  available_balance: number;
}

export interface LeaveActionHistory {
  id: number;
  actor_user_id: number;
  action: string;
  comments: string;
  created_at: string;
}

export interface LeaveApplication {
  id: number;
  user_id: number;
  leave_type: string;
  start_date: string;
  start_half: string;
  end_date: string;
  end_half: string;
  days_requested: string | number;
  reason: string;
  station_leave: boolean;
  station_address: string;
  station_contact: string;
  emergency_contact: string;
  substitute_user_id: number | null;
  unit_head_user_id: number | null;
  sanctioning_authority_user_id: number | null;
  status: "DRAFT" | "SUBMITTED" | "RECOMMENDED" | "NOT_RECOMMENDED" | "APPROVED" | "REJECTED" | "CANCELLED";
  remarks: string;
  created_at: string;
  updated_at: string;
  actions?: LeaveActionHistory[];
}

export interface ApplyLeavePayload {
  leave_type: string;
  start_date: string;
  start_half?: string;
  end_date: string;
  end_half?: string;
  reason: string;
  station_leave?: boolean;
  station_address?: string;
  station_contact?: string;
  emergency_contact?: string;
  substitute_user_id?: number | null;
}
