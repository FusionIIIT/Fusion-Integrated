/** Leave module API client communicating with /api/v1/leave/ */

export interface LeaveType {
  id: number;
  code: string;
  name: string;
  max_days_per_year: number;
  allows_half_day: boolean;
  requires_attachment: boolean;
  is_active: boolean;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  leave_type: number;
  leave_type_code: string;
  leave_type_name: string;
  year: number;
  allocated_days: number;
  used_days: number;
  remaining_days: number;
}

export interface LeaveRequest {
  id: number;
  user_id: number;
  leave_type: number;
  leave_type_code: string;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  is_half_day: boolean;
  half_day_slot?: string;
  reason: string;
  status: "DRAFT" | "PENDING_APPROVAL" | "RECOMMENDED" | "APPROVED" | "REJECTED" | "CANCELLED";
  is_station_leave: boolean;
  station_start_date?: string;
  station_end_date?: string;
  station_address?: string;
  emergency_contact_no?: string;
  attachment_path?: string;
  recommender_user_id?: number;
  recommendation_remarks?: string;
  recommended_at?: string;
  approver_user_id?: number;
  rejection_reason?: string;
  approval_remarks?: string;
  approved_at?: string;
  created_at: string;
}

export interface LeaveLedgerItem {
  id: number;
  user_id: number;
  leave_type_code: string;
  leave_type_name: string;
  transaction_type: string;
  days: number;
  balance_after: number;
  remarks: string;
  created_at: string;
}

const BASE_URL = "/api/v1/leave";

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("access_token");
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export const leaveApi = {
  getLeaveTypes: () => request<LeaveType[]>("/types"),
  getMyBalances: () => request<LeaveBalance[]>("/balances"),
  getMyRequests: () => request<LeaveRequest[]>("/requests"),
  submitLeaveRequest: (data: Partial<LeaveRequest>) =>
    request<LeaveRequest>("/requests", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  cancelLeaveRequest: (id: number) =>
    request<LeaveRequest>(`/requests/${id}/cancel`, {
      method: "POST",
    }),
  getPendingApprovals: () => request<LeaveRequest[]>("/approvals"),
  recommendRequest: (id: number, remarks: string) =>
    request<LeaveRequest>(`/requests/${id}/recommend`, {
      method: "POST",
      body: JSON.stringify({ remarks }),
    }),
  approveOrRejectRequest: (id: number, action: "approve" | "reject", remarks: string) =>
    request<LeaveRequest>(`/requests/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ action, remarks }),
    }),
  getLedger: () => request<LeaveLedgerItem[]>("/ledger"),
};
