export interface LeaveBalance {
  id: number;
  employee_id: string;
  is_faculty: boolean;
  year: number;
  leave_type: string;
  total_allocated: string;
  carried_forward: string;
  used_days: string;
  lapsed_days: string;
  converted_days: string;
  remaining_days: string;
}

export interface LeaveHistory {
  id: number;
  actor_id: string;
  from_status: string;
  to_status: string;
  action: string;
  remarks: string;
  timestamp: string;
}

export interface LeaveApplication {
  id: number;
  applicant_id: string;
  is_faculty: boolean;
  is_director: boolean;
  leave_type: string;
  start_date: string;
  end_date: string;
  total_days: string;
  is_half_day: boolean;
  reason: string;
  requires_station_leave: boolean;
  station_leave_address: string;
  substitute_id: string;
  substitute_status: string;
  substitute_remarks: string;
  status: string;
  unit_head_id: string;
  unit_head_recommendation: string;
  unit_head_remarks: string;
  sanctioner_id: string;
  sanction_decision: string;
  sanction_remarks: string;
  is_extension: boolean;
  parent_leave: number | null;
  actual_resumption_date: string | null;
  actual_days_availed: string | null;
  is_offline_record: boolean;
  created_at: string;
  history?: LeaveHistory[];
}

export async function fetchMyBalances(): Promise<LeaveBalance[]> {
  const res = await fetch("/api/v1/elm/balances", { credentials: "include" });
  if (!res.ok) throw new Error("Failed to load leave balances");
  return res.json();
}

export async function fetchMyApplications(): Promise<LeaveApplication[]> {
  const res = await fetch("/api/v1/elm/applications", { credentials: "include" });
  if (!res.ok) throw new Error("Failed to load leave applications");
  return res.json();
}

export async function createLeaveApplication(payload: Record<string, unknown>): Promise<LeaveApplication> {
  const res = await fetch("/api/v1/elm/applications", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to submit leave request");
  }
  return res.json();
}

export async function withdrawLeaveApplication(id: number, reason: string): Promise<LeaveApplication> {
  const res = await fetch(`/api/v1/elm/applications/${id}/withdraw`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) throw new Error("Failed to withdraw application");
  return res.json();
}

export async function cancelLeaveApplication(id: number, reason: string): Promise<LeaveApplication> {
  const res = await fetch(`/api/v1/elm/applications/${id}/cancel`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) throw new Error("Failed to cancel approved application");
  return res.json();
}

export async function extendLeaveApplication(id: number, newEndDate: string, reason: string): Promise<LeaveApplication> {
  const res = await fetch(`/api/v1/elm/applications/${id}/extend`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_end_date: newEndDate, reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to extend leave application");
  }
  return res.json();
}

export async function submitResumption(id: number, actualResumptionDate: string, remarks: string): Promise<LeaveApplication> {
  const res = await fetch(`/api/v1/elm/applications/${id}/resume`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actual_resumption_date: actualResumptionDate, remarks }),
  });
  if (!res.ok) throw new Error("Failed to submit duty resumption");
  return res.json();
}

export async function fetchSubstituteRequests(): Promise<LeaveApplication[]> {
  const res = await fetch("/api/v1/elm/substitutes/requests", { credentials: "include" });
  if (!res.ok) throw new Error("Failed to fetch substitute requests");
  return res.json();
}

export async function respondSubstitute(id: number, accept: boolean, remarks: string): Promise<LeaveApplication> {
  const res = await fetch(`/api/v1/elm/substitutes/requests/${id}/respond`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accept, remarks }),
  });
  if (!res.ok) throw new Error("Failed to respond to substitute request");
  return res.json();
}

export async function fetchUnitHeadQueue(): Promise<LeaveApplication[]> {
  const res = await fetch("/api/v1/elm/approvals/unit-head", { credentials: "include" });
  if (!res.ok) throw new Error("Failed to fetch unit head queue");
  return res.json();
}

export async function reviewUnitHead(id: number, action: string, remarks: string): Promise<LeaveApplication> {
  const res = await fetch(`/api/v1/elm/approvals/unit-head/${id}/review`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, remarks }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to process unit head review");
  }
  return res.json();
}

export async function fetchSanctionQueue(): Promise<LeaveApplication[]> {
  const res = await fetch("/api/v1/elm/approvals/sanction", { credentials: "include" });
  if (!res.ok) throw new Error("Failed to fetch sanction queue");
  return res.json();
}

export async function reviewSanction(id: number, action: string, remarks: string): Promise<LeaveApplication> {
  const res = await fetch(`/api/v1/elm/approvals/sanction/${id}/review`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, remarks }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to process sanction decision");
  }
  return res.json();
}
