export interface LeaveBalance {
  id: number;
  user_id: string;
  username: string;
  user_category: string;
  category: string;
  allocated: number;
  availed: number;
  pending: number;
  balance: number;
  year: number;
}

export interface LeaveApplication {
  id: number;
  applicant_id: string;
  applicant_name: string;
  applicant_category: string;
  applicant_role: string;
  department: string;
  category: string;
  start_date: string;
  end_date: string;
  half_day_type: string;
  requested_days: number;
  purpose: string;
  is_station_leave: boolean;
  station_address?: string;
  out_of_station_start?: string;
  out_of_station_end?: string;
  emergency_contact?: string;
  substitute_id?: string;
  substitute_name?: string;
  substitute_status: string;
  status: string;
  current_authority_role: string;
  unit_head_recommendation: string;
  final_decision_by?: string;
  created_at: string;
}

const API_BASE = "/api/v1/leave";

export const leaveApi = {
  async getBalances(userId: string, year: number = 2026): Promise<LeaveBalance[]> {
    const res = await fetch(`${API_BASE}/balances/?user_id=${userId}&year=${year}`);
    return res.json();
  },

  async getApplications(params: { applicant_id?: string; status?: string; authority_role?: string }): Promise<LeaveApplication[]> {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    const res = await fetch(`${API_BASE}/applications/?${query}`);
    return res.json();
  },

  async applyForLeave(payload: any): Promise<LeaveApplication> {
    const res = await fetch(`${API_BASE}/applications/apply/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "Failed to submit leave application");
    }
    return res.json();
  },

  async respondSubstitute(payload: { substitute_id: string; application_id: number; action: "ACCEPT" | "DECLINE"; remarks?: string }) {
    const res = await fetch(`${API_BASE}/applications/substitute_respond/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  async unitHeadReview(payload: { reviewer_id: string; reviewer_name: string; application_id: number; outcome: string; remarks?: string }) {
    const res = await fetch(`${API_BASE}/applications/unit_head_review/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  async finalSanction(payload: { authority_id: string; authority_name: string; authority_role: string; application_id: number; decision: "APPROVE" | "REJECT"; remarks?: string }) {
    const res = await fetch(`${API_BASE}/applications/final_sanction/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  async withdraw(payload: { applicant_id: string; application_id: number; remarks?: string }) {
    const res = await fetch(`${API_BASE}/applications/withdraw/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  async submitResumption(payload: { applicant_id: string; application_id: number; actual_resumption_date: string; remarks?: string }) {
    const res = await fetch(`${API_BASE}/applications/submit_resumption/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return res.json();
  }
};
