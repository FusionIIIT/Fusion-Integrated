import { http } from "../../../lib/http";
import type {
  HolidayItem,
  LeaveApplication,
  LeaveBalance,
  LeaveLedgerEntry,
  SubstituteRequest,
  VacationPeriodItem,
} from "./types";

export const leaveApi = {
  getBalances: async (year?: number) => {
    const res = await http.get<{ balance: LeaveBalance; ledger: LeaveLedgerEntry[] }>(
      "/leave/balances/",
      { params: { year } }
    );
    return res.data;
  },

  getMyApplications: async () => {
    const res = await http.get<LeaveApplication[]>("/leave/applications/");
    return res.data;
  },

  getApplicationDetail: async (id: number) => {
    const res = await http.get<LeaveApplication>(`/leave/applications/${id}/`);
    return res.data;
  },

  applyForLeave: async (data: Record<string, unknown>) => {
    const res = await http.post<LeaveApplication>("/leave/applications/", data);
    return res.data;
  },

  withdrawApplication: async (id: number, reason?: string) => {
    const res = await http.delete<LeaveApplication>(`/leave/applications/${id}/`, {
      params: { reason },
    });
    return res.data;
  },

  requestCancellation: async (id: number, reason: string) => {
    const res = await http.post<LeaveApplication>(`/leave/applications/${id}/cancel/`, { reason });
    return res.data;
  },

  requestExtension: async (id: number, data: { start_date: string; end_date: string; purpose: string; substitute_user_id?: number | null }) => {
    const res = await http.post<LeaveApplication>(`/leave/applications/${id}/extend/`, data);
    return res.data;
  },

  exportApplication: async (id: number) => {
    const res = await http.get(`/leave/applications/${id}/export/`, { responseType: "blob" });
    return res.data as Blob;
  },

  printApplication: async (id: number) => {
    const res = await http.get(`/leave/applications/${id}/print/`, { responseType: "blob" });
    return res.data as Blob;
  },

  submitResumption: async (id: number, resumption_date: string, remarks?: string) => {
    const res = await http.post<LeaveApplication>(`/leave/applications/${id}/resume/`, {
      resumption_date,
      remarks,
    });
    return res.data;
  },

  getMySubstituteRequests: async () => {
    const res = await http.get<SubstituteRequest[]>("/leave/substitutes/");
    return res.data;
  },

  respondToSubstituteRequest: async (id: number, decision: "accepted" | "declined", remarks?: string) => {
    const res = await http.post<SubstituteRequest>(`/leave/substitutes/${id}/respond/`, {
      decision,
      remarks,
    });
    return res.data;
  },

  getApprovalsQueue: async () => {
    const res = await http.get<LeaveApplication[]>("/leave/approvals/");
    return res.data;
  },

  unitHeadReview: async (id: number, recommended: boolean, remarks?: string) => {
    const res = await http.post<LeaveApplication>(`/leave/approvals/${id}/unit-head-review/`, {
      recommended,
      remarks,
    });
    return res.data;
  },

  sanctionDecision: async (id: number, decision: "approved" | "rejected", remarks?: string) => {
    const res = await http.post<LeaveApplication>(`/leave/approvals/${id}/sanction/`, {
      decision,
      remarks,
    });
    return res.data;
  },

  processCancellation: async (id: number, decision: "approved" | "rejected", remarks?: string) => {
    const res = await http.post<LeaveApplication>(`/leave/approvals/${id}/review-cancellation/`, {
      decision,
      remarks,
    });
    return res.data;
  },

  forwardApproval: async (id: number, remarks?: string) => {
    const res = await http.post<LeaveApplication>(`/leave/approvals/${id}/forward/`, { remarks });
    return res.data;
  },

  processResumption: async (id: number, remarks?: string) => {
    const res = await http.post<LeaveApplication>(`/leave/approvals/${id}/review-resumption/`, {
      remarks,
    });
    return res.data;
  },

  getCalendar: async (year?: number) => {
    const res = await http.get<{ holidays: HolidayItem[]; vacation_periods: VacationPeriodItem[] }>(
      "/leave/calendar/",
      { params: { year } }
    );
    return res.data;
  },

  recordOfflineSync: async (data: Record<string, unknown>) => {
    const res = await http.post<LeaveApplication>("/leave/admin/offline-sync/", data);
    return res.data;
  },

  maintainRecord: async (id: number, data: Record<string, unknown>) => {
    const res = await http.patch<LeaveApplication>(`/leave/admin/applications/${id}/`, data);
    return res.data;
  },

  saveConfig: async (key: string, value: unknown, description = "") => {
    const res = await http.put("/leave/admin/config/", { key, value, description });
    return res.data;
  },

  addCalendarEntries: async (year: number, entries: Array<{ name: string; date: string; kind: "closed" | "restricted" }>) => {
    const res = await http.post<HolidayItem[]>("/leave/calendar/admin/", { year, entries });
    return res.data;
  },

  publishCalendar: async (year: number, holiday_ids: number[]) => {
    const res = await http.post(`/leave/calendar/${year}/publish/`, { holiday_ids });
    return res.data;
  },
};
