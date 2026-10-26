/** Types for the elm module; they mirror modules/elm/api/serializers.py. */
export const LEAVE_CATEGORIES = ["CL", "RH", "SCL", "EL", "COL", "VL"] as const;

export type LeaveCategory = (typeof LEAVE_CATEGORIES)[number];

export type LeaveRequest = {
  id: number;
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day: boolean;
  reason: string;
  station_leave_details: string | null;
  substitute_user_id: number | null;
  status: string;
  created_at: string;
};

export type Balance = {
  category: LeaveCategory;
  amount: string;
};

export type ApplyInput = {
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  reason: string;
  half_day?: boolean;
  station_leave_details?: string | null;
  substitute_user_id?: number | null;
};
