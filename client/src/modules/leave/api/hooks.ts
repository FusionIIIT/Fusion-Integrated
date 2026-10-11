/** Data access for the leave module.
 *
 *  Every mutation invalidates the keys it can affect, so a decision taken in
 *  the approvals queue cannot leave a stale status on the employee's own page. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  HolidayCalendar, HierarchyRule, LeaveBalance, LeavePolicy, LeaveRequest,
  LeaveResumption, LeaveSummary, LedgerEntry, Page, SlaThreshold,
  SubstituteAssignment, ValidationResult, WorkflowTask,
} from "./types";

const KEY = "leave";

export const keys = {
  summary: () => [KEY, "summary"] as const,
  mine: () => [KEY, "mine"] as const,
  request: (id: number) => [KEY, "request", id] as const,
  requests: (f?: unknown) => [KEY, "requests", f] as const,
  tasks: (status: string) => [KEY, "tasks", status] as const,
  substitutions: () => [KEY, "substitutions"] as const,
  resumptions: () => [KEY, "resumptions"] as const,
  balance: (userId: number) => [KEY, "balance", userId] as const,
  ledger: (userId: number) => [KEY, "ledger", userId] as const,
  policy: () => [KEY, "policy"] as const,
  hierarchy: () => [KEY, "hierarchy"] as const,
  calendar: () => [KEY, "calendar"] as const,
  sla: () => [KEY, "sla"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Employee ------------------------------------------------------------------
export function useLeaveSummary() {
  return useQuery({
    queryKey: keys.summary(),
    queryFn: async () =>
      (await http.get<LeaveSummary>("/leave/summary")).data,
    staleTime: 15_000,
  });
}

export function useMyLeaveRequests() {
  return useQuery({
    queryKey: keys.mine(),
    queryFn: async () =>
      (await http.get<Page<LeaveRequest>>("/leave/requests/mine")).data,
    staleTime: 15_000,
  });
}

export function useLeaveRequest(id: number | undefined) {
  return useQuery({
    queryKey: keys.request(id ?? 0),
    queryFn: async () =>
      (await http.get<LeaveRequest>(`/leave/requests/${id}`)).data,
    enabled: Boolean(id),
  });
}

export function useLeaveLedger(userId: number, leaveYear?: number) {
  return useQuery({
    queryKey: keys.ledger(userId),
    queryFn: async () => (await http.get<Page<LedgerEntry>>(
      `/leave/accounts/${userId}/ledger`,
      { params: leaveYear ? { leave_year: leaveYear } : undefined })).data,
    enabled: Boolean(userId),
  });
}

/** The "will this work?" call, made before submitting (EL-UC-001 M4). */
export function useValidateLeave() {
  return useMutation({
    mutationFn: async (body: {
      category: string; period_from: string; period_to: string; half?: string;
    }) => (await http.post<ValidationResult>(
      "/leave/requests/validate", body)).data,
  });
}

export function useApplyLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      category: string; period_from: string; period_to: string; half?: string;
      purpose?: string; substitute_user_id?: number | null;
      station_leave?: Record<string, unknown>;
    }) => (await http.post<LeaveRequest>("/leave/requests", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdraw() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason?: string }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/withdraw`,
                                     { reason: reason ?? "" })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRequestCancellation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, note }: { id: number; note?: string }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/cancellation`,
                                     { note: note ?? "" })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRequestExtension() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, period_to, purpose, substitute_user_id }: {
      id: number; period_to: string; purpose?: string;
      substitute_user_id?: number | null;
    }) => (await http.post<LeaveRequest>(`/leave/requests/${id}/extension`,
                                        { period_to, purpose, substitute_user_id })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, actual_date, remarks }: {
      id: number; actual_date: string; remarks?: string;
    }) => (await http.post<LeaveResumption>(`/leave/requests/${id}/resumption`,
                                           { actual_date, remarks })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useNominateReplacement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, substitute_user_id }: {
      id: number; substitute_user_id: number;
    }) => (await http.post<SubstituteAssignment>(
      `/leave/requests/${id}/substitute`, { substitute_user_id })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useMySubstitutions() {
  return useQuery({
    queryKey: keys.substitutions(),
    queryFn: async () => (await http.get<Page<SubstituteAssignment>>(
      "/leave/substitutions")).data,
    staleTime: 15_000,
  });
}

/** A substitute holds no permission: the nomination is the authority. */
export function useRespondToSubstitution() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, accept, note }: {
      id: number; accept: boolean; note?: string;
    }) => (await http.post<SubstituteAssignment>(
      `/leave/substitutions/${id}/respond`, { accept, note })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Approver ------------------------------------------------------------------
export function useLeaveTasks(status = "pending") {
  return useQuery({
    queryKey: keys.tasks(status),
    queryFn: async () => (await http.get<Page<WorkflowTask>>(
      "/leave/tasks", { params: { status } })).data,
    staleTime: 10_000,
  });
}

/** A decision acts on the TASK, not the request: "may I decide this?" then has
 *  one answer per row rather than one per view. */
export function useDecideTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, note, recommendation }: {
      id: number; action: string; note?: string; recommendation?: string;
    }) => (await http.post<LeaveRequest>(`/leave/tasks/${id}/decision`,
                                        { action, note, recommendation })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useResumptions() {
  return useQuery({
    queryKey: keys.resumptions(),
    queryFn: async () => (await http.get<Page<LeaveResumption>>(
      "/leave/resumptions")).data,
    staleTime: 15_000,
  });
}

export function useReviewResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, note }: { id: number; note?: string }) =>
      (await http.post<LeaveResumption>(`/leave/resumptions/${id}/review`,
                                       { note: note ?? "" })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Records -------------------------------------------------------------------
export function useLeaveRecords(filters?: { category?: string; status?: string }) {
  return useQuery({
    queryKey: keys.requests(filters),
    queryFn: async () => (await http.get<Page<LeaveRequest>>(
      "/leave/records", { params: filters })).data,
    staleTime: 15_000,
  });
}

export function useBalanceFor(userId: number, leaveYear?: number) {
  return useQuery({
    queryKey: keys.balance(userId),
    queryFn: async () => (await http.get<{ user_id: number; results: LeaveBalance[] }>(
      `/leave/accounts/${userId}`,
      { params: leaveYear ? { leave_year: leaveYear } : undefined })).data,
    enabled: Boolean(userId),
  });
}

/** EL-UC-016 — record leave already sanctioned on paper. Not an approval. */
export function useRecordOffline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      employee_user_id: number; category: string; period_from: string;
      period_to: string; evidence_reference: string; purpose?: string;
      certified_by?: string;
    }) => (await http.post<LeaveRequest>("/leave/records/offline", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAdjustBalance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      employee_user_id: number; category: string; days: string; note: string;
      leave_year?: number;
    }) => (await http.post<LeaveBalance>("/leave/accounts/adjust", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Configuration -------------------------------------------------------------
export function usePolicy() {
  return useQuery({
    queryKey: keys.policy(),
    queryFn: async () =>
      (await http.get<Page<LeavePolicy>>("/leave/config/policy")).data,
    staleTime: 60_000,
  });
}

export function useSavePolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.put<LeavePolicy>("/leave/config/policy", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useHierarchy() {
  return useQuery({
    queryKey: keys.hierarchy(),
    queryFn: async () =>
      (await http.get<{ results: HierarchyRule[] }>("/leave/config/hierarchy"))
        .data,
    staleTime: 60_000,
  });
}

export function useReplaceHierarchy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { category: string; steps: Record<string, unknown>[] }) =>
      (await http.put<{ replaced: number; category: string }>(
        "/leave/config/hierarchy", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCalendars() {
  return useQuery({
    queryKey: keys.calendar(),
    queryFn: async () => (await http.get<Page<HolidayCalendar>>(
      "/leave/config/calendar")).data,
    staleTime: 60_000,
  });
}

export function useSaveCalendar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { leave_year: number; label?: string;
                               entries: Record<string, unknown>[] }) =>
      (await http.post<HolidayCalendar>("/leave/config/calendar", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

/** Publishing is what makes a calendar govern (BR-EL-031). */
export function usePublishCalendar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<HolidayCalendar>(
        `/leave/config/calendar/${id}/publish`, {})).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSlaThresholds() {
  return useQuery({
    queryKey: keys.sla(),
    queryFn: async () =>
      (await http.get<Page<SlaThreshold>>("/leave/config/sla")).data,
    staleTime: 60_000,
  });
}

export function useSaveSlaThreshold() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      task_class: string; reminder_hours: number; escalation_hours: number;
      escalation_action?: string; escalate_to_role?: string;
    }) => (await http.put<SlaThreshold>("/leave/config/sla", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}
