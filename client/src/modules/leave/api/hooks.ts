/** Data access for the leave module.
 *
 *  Every mutation invalidates the whole leave key space: a submission moves a
 *  request between queues that several screens read, and invalidating only the
 *  screen that made the call is how an approvals list keeps showing a task
 *  somebody already decided.
 */
import {
  useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";

import { errorMessage, http } from "../../../lib/http";
import type {
  AdminConfig, ApprovalTask, BalanceAdjustment, CancellationRequest,
  ExtensionRequest, HolidayCalendarSerializer, LeaveBalance, LeaveLedgerEntry,
  LeavePolicySerializer, LeaveRequest, NotificationOutbox,
  OrganizationalUnit, ResumptionRequest, SlaThresholdSerializer,
  SubstituteNomination, VacationPeriodSerializer, YearEndReport,
} from "./types";

const KEY = "leave";

export const keys = {
  mine: (f?: unknown) => [KEY, "my-requests", f] as const,
  counts: () => [KEY, "counts"] as const,
  drafts: () => [KEY, "drafts"] as const,
  approvals: () => [KEY, "approvals"] as const,
  substitutions: () => [KEY, "substitutions"] as const,
  balances: (year?: number) => [KEY, "balances", year] as const,
  ledger: (f?: unknown) => [KEY, "ledger", f] as const,
  lifecycle: () => [KEY, "lifecycle"] as const,
  adminConfig: () => [KEY, "admin-config"] as const,
  policy: () => [KEY, "policy"] as const,
  exceptions: () => [KEY, "exceptions"] as const,
  overdue: () => [KEY, "overdue"] as const,
  yearEndStatus: () => [KEY, "year-end-status"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- my requests --------------------------------------------------------------

export function useMyRequests(filters?: { status?: string; category?: string;
                                         year?: number }) {
  return useQuery({
    queryKey: keys.mine(filters),
    queryFn: async () => (await http.get<LeaveRequest[]>("/leave/my-requests",
                                                        { params: filters })).data,
  });
}

export function useRequestCounts() {
  return useQuery({
    queryKey: keys.counts(),
    queryFn: async () =>
      (await http.get<Record<string, number>>("/leave/my-requests/counts")).data,
  });
}

export function useDrafts() {
  return useQuery({
    queryKey: keys.drafts(),
    queryFn: async () => (await http.get<LeaveRequest[]>("/leave/drafts")).data,
  });
}

export function useCreateDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<LeaveRequest>) =>
      (await http.post<LeaveRequest>("/leave/requests", body)).data,
    onSuccess: (row) => {
      invalidateAll(qc);
      qc.setQueryData(keys.drafts(),
        (old: LeaveRequest[] | undefined) => [row, ...(old ?? [])]);
    },
  });
}

/** Takes the id in the variables rather than as an argument, because a draft's id
 *  is only known once the server has created it. */
export function useSubmitRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, note = "" }: { id: number; note?: string }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/submit`,
                                     { note })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdrawRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/withdraw`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: { id: number } & Partial<LeaveRequest>) =>
      (await http.patch<LeaveRequest>(`/leave/requests/${id}`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await http.delete(`/leave/requests/${id}`);
      return id;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRequestOverlaps(id: number | undefined) {
  return useQuery({
    queryKey: [KEY, "overlaps", id],
    queryFn: async () =>
      (await http.get<{ conflicting: LeaveRequest[]; exempt: LeaveRequest[] }>(
        `/leave/requests/${id}/overlaps`)).data,
    enabled: id != null,
  });
}

// -- substitutions ------------------------------------------------------------

export function useSubstitutions() {
  return useQuery({
    queryKey: keys.substitutions(),
    queryFn: async () =>
      (await http.get<SubstituteNomination[]>("/leave/substitutions")).data,
  });
}

export function useRespondToNomination() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, accept }: { id: number; accept: boolean }) =>
      (await http.post<SubstituteNomination>(
        `/leave/substitutions/${id}/respond`, { accept })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useNominateSubstitute(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { nominee_user_id: number;
                              extension_request_id?: number | null }) =>
      (await http.post<SubstituteNomination>(
        `/leave/requests/${id}/nominate-substitute`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- approvals ----------------------------------------------------------------

export function useApprovals() {
  return useQuery({
    queryKey: keys.approvals(),
    queryFn: async () =>
      (await http.get<ApprovalTask[]>("/leave/approvals")).data,
  });
}

/** One deciding endpoint for every edge, which is why the payload is the same
 *  shape whichever authority is acting. The id travels in the variables with the
 *  rest of the decision, so the row being decided cannot drift from the row the
 *  dialog was opened for. */
export function useDecideTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, approve, note = "", recommendation = "" }: {
      id: number; approve: boolean; note?: string; recommendation?: string }) =>
      (await http.post(`/leave/approvals/${id}/decision`,
                       { approve, note, recommendation })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- accounts -----------------------------------------------------------------

export function useBalances(year?: number) {
  return useQuery({
    queryKey: keys.balances(year),
    queryFn: async () =>
      (await http.get<LeaveBalance[]>("/leave/balances",
                                     { params: year ? { year } : {} })).data,
  });
}

export function useLedger(filters?: { user_id?: number; year?: number;
                                     category?: string }) {
  return useQuery({
    queryKey: keys.ledger(filters),
    queryFn: async () =>
      (await http.get<LeaveLedgerEntry[]>("/leave/ledger",
                                          { params: filters })).data,
  });
}

export function useAdjustBalance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: BalanceAdjustment) => {
      await http.post("/leave/balances/adjust", body);
      return body;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReconcileAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { user_id: number; year: number }) =>
      (await http.post<LeaveBalance[]>("/leave/ledger/reconcile", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- lifecycle ----------------------------------------------------------------

export interface LifecycleBundle {
  cancellations: CancellationRequest[];
  extensions: ExtensionRequest[];
  resumptions: ResumptionRequest[];
}

export function useLifecycle() {
  return useQuery({
    queryKey: keys.lifecycle(),
    queryFn: async () =>
      (await http.get<LifecycleBundle>("/leave/lifecycle")).data,
  });
}

export function useRequestCancellation(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (reason: string) =>
      (await http.post<CancellationRequest>(`/leave/requests/${id}/cancellation`,
                                            { reason })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRequestExtension(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { additional_start_date: string;
                              additional_end_date: string; reason: string }) =>
      (await http.post<ExtensionRequest>(`/leave/requests/${id}/extension`,
                                         body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitResumption(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { actual_resumption_date: string;
                              details?: string }) =>
      (await http.post<ResumptionRequest>(`/leave/requests/${id}/resumption`,
                                          body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- administration -----------------------------------------------------------

export function useAdminConfig() {
  return useQuery({
    queryKey: keys.adminConfig(),
    queryFn: async () =>
      (await http.get<AdminConfig>("/leave/admin/config")).data,
  });
}

export function useUpdatePolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<LeavePolicySerializer>) =>
      (await http.patch<LeavePolicySerializer>("/leave/admin/policy", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSaveHoliday() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { year: number; date: string; name: string;
                              is_restricted_holiday?: boolean }) => {
      await http.post("/leave/admin/calendar/holidays", body);
      return body;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublishCalendar(year: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      (await http.post<HolidayCalendarSerializer>(
        `/leave/admin/calendar/holidays/${year}/publish`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSaveVacationPeriod() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Omit<VacationPeriodSerializer, "id" | "year">) =>
      (await http.post<VacationPeriodSerializer>(
        "/leave/admin/calendar/vacation-periods", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSaveRoute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string; leave_category?: string;
                              org_unit_id?: number | null;
                              steps: Record<string, unknown>[] }) =>
      (await http.post<AdminConfig["routes"][number]>(
        "/leave/admin/routes", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSaveUnit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string; head_user_id?: number | null }) =>
      (await http.post<OrganizationalUnit>("/leave/admin/units", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSaveThreshold() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<SlaThresholdSerializer> & {
      task_kind: string }) =>
      (await http.post<SlaThresholdSerializer>("/leave/admin/thresholds",
                                                body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRecordOfflineLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { user_id: number; category: string;
                              start_date: string; end_date: string;
                              sanction_reference: string; purpose?: string }) => {
      await http.post("/leave/admin/offline-leave", body);
      return body;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- exceptions and year-end --------------------------------------------------

export function useExceptionOverview() {
  return useQuery({
    queryKey: keys.exceptions(),
    queryFn: async () =>
      (await http.get<Record<string, number>>("/leave/exceptions/overview")).data,
  });
}

export function useOverdueOutOfOffice() {
  return useQuery({
    queryKey: keys.overdue(),
    queryFn: async () =>
      (await http.get<LeaveRequest[]>(
        "/leave/exceptions/overdue-out-of-office")).data,
  });
}

export function useYearEndStatus() {
  return useQuery({
    queryKey: keys.yearEndStatus(),
    queryFn: async () =>
      (await http.get<{ today: string; year_end_month: number; due: boolean;
                         pending_tasks: number }>(
        "/leave/admin/year-end/status")).data,
  });
}

export function useRunYearEnd() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { year: number; dry_run?: boolean;
                              only_user_ids?: number[] }) =>
      (await http.post<YearEndReport>("/leave/admin/year-end/run", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export { errorMessage };