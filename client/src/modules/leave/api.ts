import { http } from "../../lib/http";

export interface LeaveBalance {
  id: number;
  user_id: number;
  year: number;
  category: "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";
  credited: number;
  availed: number;
  available_balance: number;
}

export interface LeaveApplicationAudit {
  id: number;
  actor_id: number;
  action: string;
  from_status: string;
  to_status: string;
  remarks: string;
  created_at: string;
}

export interface LeaveApplication {
  id: number;
  user_id: number;
  category: "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";
  start_date: string;
  end_date: string;
  half_day_slot: "none" | "first_half" | "second_half";
  calculated_days: number;
  reason: string;
  status:
    | "draft"
    | "submitted"
    | "substitute_pending"
    | "unit_head_pending"
    | "sanctioning_pending"
    | "approved"
    | "rejected"
    | "withdrawn"
    | "cancelled"
    | "extended"
    | "resumed";
  station_leave_applied: boolean;
  station_leave_address: string;
  station_leave_contact: string;
  substitute_id: number | null;
  substitute_status: "none" | "pending" | "accepted" | "declined";
  unit_head_id: number | null;
  unit_head_recommendation: "pending" | "recommended" | "not_recommended";
  sanctioning_authority_id: number | null;
  created_at: string;
  audits: LeaveApplicationAudit[];
}

export const leaveApi = {
  getBalances: async (year?: number): Promise<LeaveBalance[]> => {
    const res = await http.get<LeaveBalance[]>("/leave/balances/", { params: { year } });
    return res.data;
  },

  getApplications: async (): Promise<LeaveApplication[]> => {
    const res = await http.get<LeaveApplication[]>("/leave/applications/");
    return res.data;
  },

  getApplicationDetail: async (id: number): Promise<LeaveApplication> => {
    const res = await http.get<LeaveApplication>(`/leave/applications/${id}/`);
    return res.data;
  },

  applyLeave: async (data: {
    category: string;
    start_date: string;
    end_date: string;
    half_day_slot?: string;
    reason?: string;
    substitute_id?: number | null;
    unit_head_id?: number | null;
    sanctioning_authority_id?: number | null;
    station_leave_applied?: boolean;
    station_leave_address?: string;
    station_leave_contact?: string;
    submit_now?: boolean;
  }): Promise<LeaveApplication> => {
    const res = await http.post<LeaveApplication>("/leave/applications/", data);
    return res.data;
  },

  withdrawApplication: async (id: number): Promise<LeaveApplication> => {
    const res = await http.post<LeaveApplication>(`/leave/applications/${id}/withdraw/`);
    return res.data;
  },

  cancelApplication: async (id: number, reason: string): Promise<LeaveApplication> => {
    const res = await http.post<LeaveApplication>(`/leave/applications/${id}/cancel/`, { reason });
    return res.data;
  },

  getSubstituteRequests: async (): Promise<LeaveApplication[]> => {
    const res = await http.get<LeaveApplication[]>("/leave/substitute/requests/");
    return res.data;
  },

  respondSubstitute: async (id: number, accept: boolean, remarks?: string): Promise<LeaveApplication> => {
    const res = await http.post<LeaveApplication>(`/leave/substitute/${id}/respond/`, { accept, remarks });
    return res.data;
  },

  getApprovalQueue: async (): Promise<LeaveApplication[]> => {
    const res = await http.get<LeaveApplication[]>("/leave/reviews/");
    return res.data;
  },

  reviewUnitHead: async (id: number, approve_or_recommend: boolean, remarks?: string): Promise<LeaveApplication> => {
    const res = await http.post<LeaveApplication>(`/leave/reviews/${id}/unit-head/`, { approve_or_recommend, remarks });
    return res.data;
  },

  decideSanction: async (id: number, approve: boolean, remarks?: string): Promise<LeaveApplication> => {
    const res = await http.post<LeaveApplication>(`/leave/reviews/${id}/sanction/`, { approve, remarks });
    return res.data;
  },
};
