import { http } from "../../lib/http";
import type {
  HolidayCalendar,
  LeaveBalance,
  LeaveRequest,
  VacationPeriod,
} from "./types";

export const leaveApi = {
  // My leaves & balances
  getMyLeaves: async (status?: string): Promise<LeaveRequest[]> => {
    const res = await http.get<LeaveRequest[]>("/leave/mine/", {
      params: status ? { status } : undefined,
    });
    return res.data;
  },

  getMyBalances: async (year?: number): Promise<LeaveBalance[]> => {
    const res = await http.get<LeaveBalance[]>("/leave/balances/", {
      params: year ? { year } : undefined,
    });
    return res.data;
  },

  getLeaveDetail: async (id: number): Promise<LeaveRequest> => {
    const res = await http.get<LeaveRequest>(`/leave/${id}/`);
    return res.data;
  },

  applyLeave: async (payload: {
    category: string;
    start_date: string;
    end_date: string;
    reason: string;
    half_day?: string;
    substitute_user_id?: number | null;
    station_leave?: boolean;
    station_address?: string;
    station_contact?: string;
    station_start_date?: string | null;
    station_end_date?: string | null;
    medical_certificate_url?: string;
  }): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>("/leave/apply/", payload);
    return res.data;
  },

  withdrawLeave: async (id: number, reason: string): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>(`/leave/${id}/withdraw/`, { reason });
    return res.data;
  },

  cancelLeave: async (id: number, cancellation_reason: string): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>(`/leave/${id}/cancel/`, { cancellation_reason });
    return res.data;
  },

  extendLeave: async (id: number, extended_end_date: string, reason: string): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>(`/leave/${id}/extend/`, { extended_end_date, reason });
    return res.data;
  },

  resumeLeave: async (id: number, actual_resumption_date: string, remarks?: string): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>(`/leave/${id}/resume/`, { actual_resumption_date, remarks });
    return res.data;
  },

  // Substitute requests
  getSubstituteRequests: async (pendingOnly = false): Promise<LeaveRequest[]> => {
    const res = await http.get<LeaveRequest[]>("/leave/substitute/", {
      params: pendingOnly ? { pending: "true" } : undefined,
    });
    return res.data;
  },

  respondSubstitute: async (id: number, accepted: boolean, remarks?: string): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>(`/leave/substitute/${id}/respond/`, { accepted, remarks });
    return res.data;
  },

  replaceSubstitute: async (id: number, new_substitute_user_id: number): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>(`/leave/substitute/${id}/replace/`, { new_substitute_user_id });
    return res.data;
  },

  // Approvals
  getApprovals: async (status?: string): Promise<LeaveRequest[]> => {
    const res = await http.get<LeaveRequest[]>("/leave/approvals/", {
      params: status ? { status } : undefined,
    });
    return res.data;
  },

  reviewUnitHead: async (id: number, decision: string, remarks?: string): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>(`/leave/approvals/${id}/unit-head/`, { decision, remarks });
    return res.data;
  },

  decideSanction: async (id: number, approved: boolean, remarks?: string): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>(`/leave/approvals/${id}/sanction/`, { approved, remarks });
    return res.data;
  },

  reviewResumption: async (id: number, remarks?: string): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>(`/leave/approvals/${id}/resumption/`, { remarks });
    return res.data;
  },

  // Calendars
  getHolidayCalendar: async (year?: number): Promise<HolidayCalendar[]> => {
    const res = await http.get<HolidayCalendar[]>("/leave/calendar/", {
      params: year ? { year } : undefined,
    });
    return res.data;
  },

  getVacationPeriods: async (year?: number): Promise<VacationPeriod[]> => {
    const res = await http.get<VacationPeriod[]>("/leave/vacation-periods/", {
      params: year ? { year } : undefined,
    });
    return res.data;
  },

  // Admin
  recordOfflineLeave: async (payload: {
    user_id: number;
    category: string;
    start_date: string;
    end_date: string;
    reason: string;
    offline_reference: string;
  }): Promise<LeaveRequest> => {
    const res = await http.post<LeaveRequest>("/leave/admin/offline-sync/", payload);
    return res.data;
  },

  executeYearEnd: async (year: number): Promise<Record<string, unknown>> => {
    const res = await http.post<Record<string, unknown>>("/leave/admin/year-end/", { year });
    return res.data;
  },

  getPrintRecord: async (id: number): Promise<Record<string, unknown>> => {
    const res = await http.get<Record<string, unknown>>(`/leave/${id}/print/`);
    return res.data;
  },
};
