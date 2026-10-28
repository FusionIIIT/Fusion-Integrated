import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type {
  ApprovalRoute, Holiday, HolidayCalendar, LeaveBalance, LeavePolicy,
  LeaveRequest, LeaveTask, OrgUnit, Page, VacationPeriod,
} from "./types";

const KEY = "employee-leave";

export const leaveKeys = {
  balances: [KEY, "balances"] as const,
  requests: [KEY, "requests"] as const,
  tasks: [KEY, "tasks"] as const,
  substitutes: [KEY, "substitute-requests"] as const,
};

function invalidateLeave(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: [KEY] });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: leaveKeys.balances,
    queryFn: async () => (await http.get<LeaveBalance[]>("/elm/balances")).data,
  });
}

export function useMyLeaveRequests() {
  return useQuery({
    queryKey: leaveKeys.requests,
    queryFn: async () =>
      (await http.get<Page<LeaveRequest>>("/elm/requests")).data,
  });
}

export function useLeaveTasks() {
  return useQuery({
    queryKey: leaveKeys.tasks,
    queryFn: async () => (await http.get<Page<LeaveTask>>("/elm/tasks")).data,
  });
}

export function useSubstituteRequests() {
  return useQuery({
    queryKey: leaveKeys.substitutes,
    queryFn: async () =>
      (await http.get<Page<LeaveRequest>>("/elm/substitute-requests")).data,
  });
}

export function useLeavePolicies(enabled = true) {
  return useQuery({
    queryKey: [KEY, "policies"],
    queryFn: async () => (await http.get<Page<LeavePolicy>>("/elm/policies")).data,
    enabled,
  });
}

export function useUpdateLeavePolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      id: number;
      reminder_after_hours: number;
      escalate_after_hours: number;
      escalation_user_id: number | null;
    }) => (await http.patch<LeavePolicy>(`/elm/policies/${data.id}`, {
      reminder_after_hours: data.reminder_after_hours,
      escalate_after_hours: data.escalate_after_hours,
      escalation_user_id: data.escalation_user_id,
    })).data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function useCreateLeavePolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      year: number;
      reminder_after_hours: number;
      escalate_after_hours: number;
    }) => (await http.post<LeavePolicy>("/elm/policies", data)).data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function useOrgUnits(enabled = true) {
  return useQuery({
    queryKey: [KEY, "units"],
    queryFn: async () => (await http.get<Page<OrgUnit>>("/elm/units")).data,
    enabled,
  });
}

export function useCreateOrgUnit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      code: string; name: string; unit_head_user_id: number;
    }) => (await http.post<OrgUnit>("/elm/units", data)).data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function useApprovalRoutes(enabled = true) {
  return useQuery({
    queryKey: [KEY, "approval-routes"],
    queryFn: async () =>
      (await http.get<Page<ApprovalRoute>>("/elm/approval-routes")).data,
    enabled,
  });
}

export function useCreateApprovalRoute() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      category: string;
      unit_id: number | null;
      designation: string;
      steps: { user_id: number; role: string }[];
      is_active: boolean;
    }) => (await http.post<ApprovalRoute>("/elm/approval-routes", data)).data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function useHolidayCalendars(enabled = true) {
  return useQuery({
    queryKey: [KEY, "calendars"],
    queryFn: async () =>
      (await http.get<Page<HolidayCalendar>>("/elm/calendars")).data,
    enabled,
  });
}

export function useCreateHolidayCalendar() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { year: number; name: string }) =>
      (await http.post<HolidayCalendar>("/elm/calendars", data)).data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function useCreateHoliday(calendarId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      date: string; name: string; kind: "closed" | "restricted";
    }) => (await http.post<Holiday>(
      `/elm/calendars/${calendarId}/holidays`, data,
    )).data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function usePublishHolidayCalendar() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<HolidayCalendar>(`/elm/calendars/${id}/publish`, {})).data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function useCreateVacationPeriod() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      academic_year: string;
      label: string;
      starts_on: string;
      ends_on: string;
      source: string;
    }) => (await http.post<VacationPeriod>("/elm/vacation-periods", data)).data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function useMaintainEmployeeProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      user_id: number;
      employee_kind: "faculty" | "staff";
      unit_id: number;
      designation: string;
      requires_substitute: boolean;
      is_director: boolean;
      is_active: boolean;
    }) => (await http.put(
      `/elm/employees/${data.user_id}/manage`,
      {
        employee_kind: data.employee_kind,
        unit_id: data.unit_id,
        designation: data.designation,
        requires_substitute: data.requires_substitute,
        is_director: data.is_director,
        is_active: data.is_active,
      },
    )).data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function useRecordOfflineLeave() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      applicant_user_id: number;
      category: string;
      starts_on: string;
      ends_on: string;
      purpose: string;
      offline_reference: string;
      offline_reason: string;
      offline_sanctioned_on: string;
    }) => (await http.post<LeaveRequest>("/elm/requests/offline", data)).data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function useMaintainLeaveRecord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      id: number;
      reason: string;
      purpose?: string;
      offline_reference?: string;
    }) => {
      const { id, ...body } = data;
      return (await http.post<LeaveRequest>(`/elm/requests/${id}/maintain`, body)).data;
    },
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function useExportLeaveRequest() {
  return useMutation({
    mutationFn: async (id: number) => {
      try {
        const response = await http.get<Blob>(`/elm/requests/${id}/export`, {
          responseType: "blob",
        });
        const filename = filenameFromDisposition(
          response.headers["content-disposition"],
          `elm-leave-request-${id}.csv`,
        );
        saveBlob(response.data, filename);
      } catch (error) {
        throw await readBlobError(error);
      }
    },
  });
}

export function useSubmitLeave() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      category: string;
      starts_on: string;
      ends_on: string;
      purpose: string;
      half_day_part?: string;
      station_leave?: boolean;
      station_destination?: string;
      station_contact?: string;
      medical_evidence?: string;
      substitute_user_id?: number;
    }) => (await http.post<LeaveRequest>("/elm/requests/create", body)).data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function useLeaveAction(path: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { id: number; body?: Record<string, unknown> }) =>
      (await http.post<LeaveRequest>(`/elm/requests/${data.id}/${path}`, data.body ?? {}))
        .data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function useSubstituteResponse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { id: number; accept: boolean }) =>
      (await http.post<LeaveRequest>(
        `/elm/substitute-requests/${data.id}/respond`,
        { accept: data.accept },
      )).data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function useDecideLeaveTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      requestId: number;
      taskId: number;
      action: "approve" | "reject" | "recommend" | "not_recommend";
      note?: string;
    }) => (await http.post<LeaveRequest>(
      `/elm/requests/${data.requestId}/tasks/${data.taskId}/decide`,
      { action: data.action, note: data.note ?? "" },
    )).data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}

export function useProcessYearEnd() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (year: number) =>
      (await http.post<{ year: number; processed_accounts: number; completed_at: string }>(
        `/elm/year-end/${year}`,
        {},
      )).data,
    onSuccess: () => invalidateLeave(queryClient),
  });
}
