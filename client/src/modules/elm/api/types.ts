export interface LeaveBalance {
  id: number;
  user_id: number;
  category: string;
  year: number;
  credited: string;
  availed: string;
  balance: string;
}

export interface SubstituteAssignment {
  id: number;
  leave_request_id: number;
  substitute_id: number;
  status: "pending" | "accepted" | "declined";
  remarks: string;
  responded_at: string | null;
}

export interface LeaveRequest {
  id: number;
  user_id: number;
  category: string;
  start_date: string;
  end_date: string;
  half_day: string | null;
  leave_days: string;
  purpose: string;
  status:
    | "submitted"
    | "awaiting_substitute"
    | "under_review"
    | "recommended"
    | "sanctioned"
    | "rejected"
    | "withdrawn"
    | "cancelled";
  is_station_leave: boolean;
  destination: string;
  emergency_contact: string;
  substitute_id: number | null;
  rejection_reason: string;
  created_at: string;
  substitute_assignments: SubstituteAssignment[];
}

export interface ApplyLeavePayload {
  category: string;
  start_date: string;
  end_date: string;
  half_day?: string;
  purpose: string;
  is_station_leave?: boolean;
  destination?: string;
  emergency_contact?: string;
  substitute_id?: number | null;
}
