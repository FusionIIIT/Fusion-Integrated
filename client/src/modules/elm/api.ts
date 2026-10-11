import { api } from "../../lib/api";

export interface LeaveBalanceRow {
  id: number;
  employee_id: number;
  leave_type: number;
  balance: number;
}

export interface LeaveApplicationPayload {
  leave_type: number;
  start_date: string;
  end_date: string;
  station_leave_details?: string;
}

export async function fetchLeaveBalances(): Promise<LeaveBalanceRow[]> {
  const { data } = await api.get<LeaveBalanceRow[]>("/v1/elm/balances");
  return data;
}

export async function submitLeaveApplication(payload: LeaveApplicationPayload) {
  const { data } = await api.post("/v1/elm/applications", payload);
  return data;
}
