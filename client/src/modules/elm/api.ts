import { http } from "../../lib/http";
import type {
  CreateLeaveCaseInput, LeaveAccount, LeaveCase, LeaveInbox, LeavePolicy,
  LeaveRequest, LeaveRequestInput, LeaveSummary,
} from "./types";

export const elmApi = {
  summary: async () => (await http.get<LeaveSummary>("/elm/summary")).data,
  requests: async () => (await http.get<LeaveRequest[]>("/elm/requests")).data,
  request: async (id: number) =>
    (await http.get<LeaveRequest>(`/elm/requests/${id}`)).data,
  createRequest: async (input: LeaveRequestInput) =>
    (await http.post<LeaveRequest>("/elm/requests", input)).data,
  action: async (id: number, action: string, note = "") =>
    (await http.post<LeaveRequest>(`/elm/requests/${id}/action`,
      { action, note })).data,
  withdraw: async (id: number) =>
    (await http.post<LeaveRequest>(`/elm/requests/${id}/withdraw`, {})).data,
  replaceSubstitute: async (id: number, substitute_user_id: number) =>
    (await http.post<LeaveRequest>(`/elm/requests/${id}/substitute`,
      { substitute_user_id })).data,
  createCase: async (
    id: number, input: CreateLeaveCaseInput,
  ) => (await http.post<LeaveCase>(`/elm/requests/${id}/cases`, input)).data,
  caseAction: async (id: number, action: string, note = "") =>
    (await http.post<LeaveCase>(`/elm/cases/${id}/action`,
      { action, note })).data,
  caseWithdraw: async (id: number) =>
    (await http.post<LeaveCase>(`/elm/cases/${id}/withdraw`, {})).data,
  replaceCaseSubstitute: async (id: number, substitute_user_id: number) =>
    (await http.post<LeaveCase>(`/elm/cases/${id}/substitute`,
      { substitute_user_id })).data,
  inbox: async () => (await http.get<LeaveInbox>("/elm/inbox")).data,
  accounts: async () => (await http.get<LeaveAccount[]>("/elm/accounts")).data,
  policies: async () => (await http.get<LeavePolicy[]>("/elm/policies")).data,
  updatePolicy: async (category: string, input: Partial<LeavePolicy>) =>
    (await http.patch<LeavePolicy>(`/elm/policies/${category}`, input)).data,
  calendar: async () => (await http.get<ElmCalendarDate[]>("/elm/calendar")).data,
  createCalendarDate: async (input: {
    date: string; kind: string; label: string;
  }) => (await http.post<ElmCalendarDate>("/elm/calendar", input)).data,
  publishCalendarDate: async (id: number) =>
    (await http.post<ElmCalendarDate>(`/elm/calendar/${id}/publish`, {})).data,
  createOrganizationUnit: async (input: OrganizationUnitInput) =>
    (await http.post<OrganizationUnitInput>("/elm/organization-units", input)).data,
  createEmployeeProfile: async (input: EmployeeProfileInput) =>
    (await http.post<EmployeeProfileInput>("/elm/employees", input)).data,
  createApprovalRoute: async (input: ApprovalRouteInput) =>
    (await http.post<ApprovalRouteInput>("/elm/approval-routes", input)).data,
  recordOfflineLeave: async (input: {
    user_id: number; category: string; start_date: string; end_date: string;
    half_day: string; purpose: string;
  }) => (await http.post<LeaveRequest>("/elm/records/offline", input)).data,
  adjustAccount: async (input: {
    user_id: number; category: string; year: number; amount: string;
    description: string;
  }) => (await http.post<LeaveAccount>("/elm/accounts", input)).data,
};

export interface OrganizationUnitInput {
  code: string;
  name: string;
  unit_head_user_id?: number | null;
  is_active: boolean;
}

export interface EmployeeProfileInput {
  user_id: number;
  employee_type: "faculty" | "staff";
  designation: string;
  organization_unit: number | null;
  is_active: boolean;
}

export interface ApprovalRouteInput {
  category: string;
  organization_unit: number | null;
  approver_user_id: number | null;
  approver_role: string;
  permission_code: "elm.leave.sanction";
  establishment_required: boolean;
  is_active: boolean;
}

export interface ElmCalendarDate {
  id: number;
  date: string;
  kind: string;
  label: string;
  is_published: boolean;
  published_at: string | null;
}