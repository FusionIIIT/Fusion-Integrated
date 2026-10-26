import { http } from "../../lib/http";

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
  reason?: string;
  station_leave_details?: string;
}

export interface LeaveApplicationRow {
  id: number;
  applicant_id: number;
  leave_type: number;
  start_date: string;
  end_date: string;
  reason: string;
  station_leave_details: string;
  status: string;
}

export async function fetchLeaveBalances(): Promise<LeaveBalanceRow[]> {
  const { data } = await http.get<LeaveBalanceRow[]>("/elm/balances");
  return data;
}

export async function submitLeaveApplication(
  payload: LeaveApplicationPayload
) {
  const { data } = await http.post("/elm/applications", payload);
  return data;
}

export async function fetchLeaveApplications(): Promise<LeaveApplicationRow[]> {
  const { data } = await http.get<LeaveApplicationRow[]>(
    "/elm/applications"
  );
  return data;
}

export async function withdrawLeaveApplication(
  id: number
): Promise<LeaveApplicationRow> {
  const { data } = await http.post<LeaveApplicationRow>(
    `/elm/applications/${id}/withdraw`
  );
  return data;
}
