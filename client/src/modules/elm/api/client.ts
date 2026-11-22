export interface LeaveBalance {
  id: number;
  employee_id: number;
  leave_type: string;
  year: number;
  allocated: string;
  availed: string;
  balance: string;
}

export interface LeaveRequest {
  id: number;
  applicant_id: number;
  leave_type: string;
  start_date: string;
  end_date: string;
  is_half_day: boolean;
  half_day_period?: string;
  purpose: string;
  is_station_leave: boolean;
  station_details?: string;
  substitute_id?: number;
  substitute_status: string;
  status: string;
  remarks: string;
  created_at: string;
}

export async function fetchBalances(): Promise<LeaveBalance[]> {
  const res = await fetch("/api/v1/elm/balances/");
  if (!res.ok) throw new Error("Failed to fetch balances");
  return res.json();
}

export async function fetchRequests(): Promise<LeaveRequest[]> {
  const res = await fetch("/api/v1/elm/requests/");
  if (!res.ok) throw new Error("Failed to fetch requests");
  return res.json();
}

export async function submitLeave(data: any): Promise<LeaveRequest> {
  const res = await fetch("/api/v1/elm/requests/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to apply leave");
  }
  return res.json();
}
