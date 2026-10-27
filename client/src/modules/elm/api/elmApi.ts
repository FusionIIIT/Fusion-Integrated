import { http } from "../../../lib/http";
import type {
  LeaveBalance,
  LeaveRequest,
  LeaveExtension,
  LeaveResumption,
  ApplyLeavePayload,
  HolidayItem,
  AcademicVacationItem,
} from "../types";

export const elmApi = {
  getBalances: async (year?: number): Promise<LeaveBalance[]> => {
    const params = year ? { year } : {};
    const res = await http.get<LeaveBalance[]>("/elm/balances/mine/", { params });
    return res.data;
  },

  getLeaves: async (): Promise<LeaveRequest[]> => {
    const res = await http.get<LeaveRequest[]>("/elm/leaves/");
    return res.data;
  },

  getLeaveDetail: async (id: number): Promise<LeaveRequest> => {
    const res = await http.get<LeaveRequest>(`/elm/leaves/${id}/`);
    return res.data;
  },

  applyLeave: async (payload: ApplyLeavePayload): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>("/elm/leaves/", payload);
    return res.data;
  },

  withdrawLeave: async (id: number, remarks: string = ""): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>(`/elm/leaves/${id}/withdraw/`, { remarks });
    return res.data;
  },

  requestCancellation: async (id: number, remarks: string = ""): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>(`/elm/leaves/${id}/request-cancellation/`, {
      remarks,
    });
    return res.data;
  },

  decideCancellation: async (
    id: number,
    action: "approve" | "reject",
    remarks: string = ""
  ): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>(`/elm/leaves/${id}/decide-cancellation/`, {
      action,
      remarks,
    });
    return res.data;
  },

  applyExtension: async (
    leaveId: number,
    extensionEndDate: string,
    reason: string
  ): Promise<LeaveExtension> => {
    const res = await http.post<LeaveExtension>(`/elm/leaves/${leaveId}/extend/`, {
      extension_end_date: extensionEndDate,
      reason,
    });
    return res.data;
  },

  submitResumption: async (
    leaveId: number,
    actualResumptionDate: string
  ): Promise<LeaveResumption> => {
    const res = await http.post<LeaveResumption>(`/elm/leaves/${leaveId}/resume/`, {
      actual_resumption_date: actualResumptionDate,
    });
    return res.data;
  },

  getExtensionQueue: async (): Promise<LeaveExtension[]> => {
    const res = await http.get<LeaveExtension[]>("/elm/extensions/queue/");
    return res.data;
  },

  reviewExtension: async (
    id: number,
    action: "approve" | "reject",
    remarks: string = ""
  ): Promise<LeaveExtension> => {
    const res = await http.post<LeaveExtension>(`/elm/extensions/${id}/review/`, {
      action,
      remarks,
    });
    return res.data;
  },

  getResumptionQueue: async (): Promise<LeaveResumption[]> => {
    const res = await http.get<LeaveResumption[]>("/elm/resumptions/queue/");
    return res.data;
  },

  reviewResumption: async (
    id: number,
    remarks: string = ""
  ): Promise<LeaveResumption> => {
    const res = await http.post<LeaveResumption>(`/elm/resumptions/${id}/review/`, {
      remarks,
    });
    return res.data;
  },

  getSubstituteQueue: async (): Promise<LeaveRequest[]> => {
    const res = await http.get<LeaveRequest[]>("/elm/substitute/queue/");
    return res.data;
  },

  respondSubstitute: async (
    id: number,
    action: "accept" | "decline",
    remarks: string = ""
  ): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>(`/elm/substitute/${id}/respond/`, {
      action,
      remarks,
    });
    return res.data;
  },

  getApprovalQueue: async (type: "unit_head" | "sanction" = "unit_head"): Promise<LeaveRequest[]> => {
    const res = await http.get<LeaveRequest[]>("/elm/approvals/queue/", {
      params: { type },
    });
    return res.data;
  },

  actApproval: async (
    id: number,
    stage: "unit_head" | "sanction",
    action: "approve" | "reject" | "recommend" | "not_recommend",
    remarks: string = ""
  ): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>(
      `/elm/approvals/${id}/`,
      { action, remarks },
      { params: { stage } }
    );
    return res.data;
  },

  processSlaSweep: async (): Promise<{
    reminded_count: number;
    escalated_count: number;
    total_pending_checked: number;
  }> => {
    const res = await http.post("/elm/admin/process-sla/");
    return res.data;
  },

  recordOfflineLeave: async (payload: {
    user_id: number;
    category: string;
    start_date: string;
    end_date: string;
    offline_reference_no: string;
    sanctioning_authority_name: string;
    sanction_date: string;
    remarks?: string;
  }): Promise<{ id: number; offline_reference_no?: string; message: string }> => {
    const res = await http.post("/elm/admin/offline-leave/", payload);
    return res.data;
  },

  runYearEndRollover: async (userId: number, year: number): Promise<Record<string, unknown>> => {
    const res = await http.post("/elm/admin/year-end-rollover/", {
      user_id: userId,
      year,
    });
    return res.data;
  },

  getHolidays: async (year?: number): Promise<HolidayItem[]> => {
    const params = year ? { year } : {};
    const res = await http.get<HolidayItem[]>("/elm/calendar/holidays/", { params });
    return res.data;
  },

  getVacations: async (): Promise<AcademicVacationItem[]> => {
    const res = await http.get<AcademicVacationItem[]>("/elm/calendar/vacations/");
    return res.data;
  },
};
