import { http } from "../../lib/http";
import type {
  DailyMenuItem,
  MessFeedback,
  MessRegistration,
  MessRoleAssignment,
  RebateRequest,
  RegistrationWindow,
} from "./types";

export const mmsApi = {
  // Roles
  getRoleAssignments: async (role?: string): Promise<MessRoleAssignment[]> => {
    const res = await http.get<MessRoleAssignment[]>("/mms/roles/", {
      params: role ? { role } : undefined,
    });
    return res.data;
  },

  getActiveRoles: async (): Promise<{ caretaker: MessRoleAssignment | null; warden: MessRoleAssignment | null }> => {
    const res = await http.get<{ caretaker: MessRoleAssignment | null; warden: MessRoleAssignment | null }>("/mms/roles/active/");
    return res.data;
  },

  assignRole: async (payload: {
    employee_id: number;
    role: "caretaker" | "warden";
    start_date: string;
    end_date?: string | null;
    remarks?: string;
  }): Promise<MessRoleAssignment> => {
    const res = await http.post<MessRoleAssignment>("/mms/roles/", payload);
    return res.data;
  },

  // Registration Window
  getCurrentWindow: async (mess_name?: string): Promise<RegistrationWindow> => {
    const res = await http.get<RegistrationWindow>("/mms/window/", {
      params: mess_name ? { mess_name } : undefined,
    });
    return res.data;
  },

  openWindow: async (payload: {
    name: string;
    start_date: string;
    end_date: string;
    mess_name?: string;
  }): Promise<RegistrationWindow> => {
    const res = await http.post<RegistrationWindow>("/mms/window/", payload);
    return res.data;
  },

  // Student Registration
  getMyRegistration: async (): Promise<MessRegistration> => {
    const res = await http.get<MessRegistration>("/mms/registration/mine/");
    return res.data;
  },

  submitRegistration: async (payload: {
    start_date: string;
    end_date?: string | null;
    mess_name?: string;
    remarks?: string;
  }): Promise<MessRegistration> => {
    const res = await http.post<MessRegistration>("/mms/registration/submit/", payload);
    return res.data;
  },

  submitDeregistration: async (registration_id: number, reason: string): Promise<MessRegistration> => {
    const res = await http.post<MessRegistration>(`/mms/registration/${registration_id}/deregister/`, { reason });
    return res.data;
  },

  // Caretaker / Warden Registration Reviews
  listRegistrations: async (params?: { status?: string; mess_name?: string }): Promise<MessRegistration[]> => {
    const res = await http.get<MessRegistration[]>("/mms/registrations/", { params });
    return res.data;
  },

  reviewRegistration: async (registration_id: number, approve: boolean, remarks?: string): Promise<MessRegistration> => {
    const res = await http.post<MessRegistration>(`/mms/registrations/${registration_id}/review/`, { approve, remarks });
    return res.data;
  },

  reviewDeregistration: async (registration_id: number, approve: boolean, remarks?: string): Promise<MessRegistration> => {
    const res = await http.post<MessRegistration>(`/mms/registrations/${registration_id}/review-deregister/`, { approve, remarks });
    return res.data;
  },

  // Menu
  getWeeklyMenu: async (mess_name?: string): Promise<DailyMenuItem[]> => {
    const res = await http.get<DailyMenuItem[]>("/mms/menu/", {
      params: mess_name ? { mess_name } : undefined,
    });
    return res.data;
  },

  updateMenuItem: async (payload: {
    day_of_week: string;
    meal_time: string;
    items: string;
    mess_name?: string;
  }): Promise<DailyMenuItem> => {
    const res = await http.post<DailyMenuItem>("/mms/menu/", payload);
    return res.data;
  },

  // Rebates
  getMyRebates: async (): Promise<RebateRequest[]> => {
    const res = await http.get<RebateRequest[]>("/mms/rebates/mine/");
    return res.data;
  },

  applyRebate: async (payload: {
    start_date: string;
    end_date: string;
    reason: string;
    mess_name?: string;
  }): Promise<RebateRequest> => {
    const res = await http.post<RebateRequest>("/mms/rebates/apply/", payload);
    return res.data;
  },

  listRebates: async (params?: { status?: string; student_id?: number }): Promise<RebateRequest[]> => {
    const res = await http.get<RebateRequest[]>("/mms/rebates/", { params });
    return res.data;
  },

  reviewRebate: async (
    rebate_id: number,
    payload: {
      approve: boolean;
      approved_start_date?: string | null;
      approved_end_date?: string | null;
      remarks?: string;
    }
  ): Promise<RebateRequest> => {
    const res = await http.post<RebateRequest>(`/mms/rebates/${rebate_id}/review/`, payload);
    return res.data;
  },

  // Feedback
  getFeedbacks: async (mess_name?: string): Promise<MessFeedback[]> => {
    const res = await http.get<MessFeedback[]>("/mms/feedback/", {
      params: mess_name ? { mess_name } : undefined,
    });
    return res.data;
  },

  submitFeedback: async (payload: {
    rating: number;
    category: string;
    comments: string;
    mess_name?: string;
  }): Promise<MessFeedback> => {
    const res = await http.post<MessFeedback>("/mms/feedback/", payload);
    return res.data;
  },
};

