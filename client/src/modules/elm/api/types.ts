export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";
export interface LeaveRequest {
  id: number; category: LeaveCategory; start_date: string; end_date: string;
  days: string; purpose: string; status: string; substitute_user_id: number | null;
  created_at: string;
}
export interface LeaveAccount { category: LeaveCategory; balance: string; year: number; }
