/** Data access hooks for Leave Management. */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  LeaveRequest,
  LeaveRequestListItem,
  LeaveBalance,
  LeavePolicy,
  HolidayCalendar,
  SubstituteRequest,
  Page,
  LeaveRequestCreate,
  LeaveRequestModify,
  LeaveRequestWithdraw,
  LeaveRequestCancel,
  LeaveRequestExtend,
  LeaveRequestResume,
  SubstituteRequestRespond,
  UnitHeadReview,
  EstablishmentReview,
  FinalSanction,
  LeaveBalanceAdjust,
  OfflineLeaveEntry as OfflineLeaveEntryType,
} from "../api/types";

const KEY = "leave";

export const keys = {
  leaveRequests: (f?: Record<string, unknown>) => [KEY, "requests", f] as const,
  leaveRequest: (id: number) => [KEY, "request", id] as const,
  leaveRequestHistory: (id: number) => [KEY, "request-history", id] as const,
  pendingApprovals: (f?: Record<string, unknown>) => [KEY, "pending-approvals", f] as const,
  substituteRequests: (f?: Record<string, unknown>) => [KEY, "substitute-requests", f] as const,
  balances: (f?: Record<string, unknown>) => [KEY, "balances", f] as const,
  policies: (f?: Record<string, unknown>) => [KEY, "policies", f] as const,
  calendar: (f?: Record<string, unknown>) => [KEY, "calendar", f] as const,
  offlineEntries: (f?: Record<string, unknown>) => [KEY, "offline-entries", f] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Leave Requests -----------------------------------------------------------

export function useLeaveRequests(filters?: {
  status?: string;
  category?: string;
  start_date_after?: string;
  start_date_before?: string;
  year?: number;
}) {
  return useQuery({
    queryKey: keys.leaveRequests(filters),
    queryFn: async () =>
      (await http.get<Page<LeaveRequestListItem>>("/leave/leave-requests", { params: filters })).data,
    staleTime: 15_000,
  });
}

export function useLeaveRequest(id: number | undefined) {
  return useQuery({
    queryKey: keys.leaveRequest(id!),
    queryFn: async () => (await http.get<LeaveRequest>(`/leave/leave-requests/${id}`)).data,
    enabled: id != null,
  });
}

export function useLeaveRequestHistory(id: number | undefined) {
  return useQuery({
    queryKey: keys.leaveRequestHistory(id!),
    queryFn: async () =>
      (await http.get<Page<{ id: number; from_status: string; to_status: string; actor_role: string; reason: string; created_at: string }>>(
        `/leave/leave-requests/${id}/history`
      )).data,
    enabled: id != null,
  });
}

export function useCreateLeaveRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: LeaveRequestCreate) =>
      (await http.post<LeaveRequest>("/leave/leave-requests", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitLeaveRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveRequest>(`/leave/leave-requests/${id}/submit`, {})).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useModifyLeaveRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: LeaveRequestModify }) =>
      (await http.patch<LeaveRequest>(`/leave/leave-requests/${id}`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdrawLeaveRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: LeaveRequestWithdraw }) =>
      (await http.post<LeaveRequest>(`/leave/leave-requests/${id}/withdraw`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCancelLeaveRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: LeaveRequestCancel }) =>
      (await http.post<LeaveRequest>(`/leave/leave-requests/${id}/cancel`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useExtendLeaveRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: LeaveRequestExtend }) =>
      (await http.post<LeaveRequest>(`/leave/leave-requests/${id}/extend`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useResumeLeaveRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: LeaveRequestResume }) =>
      (await http.post<LeaveRequest>(`/leave/leave-requests/${id}/resume`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Pending Approvals --------------------------------------------------------

export function usePendingApprovals(filters?: { status?: string; category?: string }) {
  return useQuery({
    queryKey: keys.pendingApprovals(filters),
    queryFn: async () =>
      (await http.get<Page<LeaveRequestListItem>>("/leave/pending-approvals", { params: filters })).data,
    staleTime: 15_000,
  });
}

// -- Approval Actions ---------------------------------------------------------

export function useUnitHeadReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: UnitHeadReview }) =>
      (await http.post<LeaveRequest>(`/leave/approvals/${id}/unit-head-review`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useEstablishmentReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: EstablishmentReview }) =>
      (await http.post<LeaveRequest>(`/leave/approvals/${id}/establishment-review`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useFinalSanction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: FinalSanction }) =>
      (await http.post<LeaveRequest>(`/leave/approvals/${id}/final-sanction`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Substitute Requests ------------------------------------------------------

export function useSubstituteRequests(filters?: { status?: string }) {
  return useQuery({
    queryKey: keys.substituteRequests(filters),
    queryFn: async () =>
      (await http.get<Page<SubstituteRequest>>("/leave/substitute-requests", { params: filters })).data,
    staleTime: 15_000,
  });
}

export function useRespondToSubstituteRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: SubstituteRequestRespond }) =>
      (await http.post<SubstituteRequest>(`/leave/substitute-requests/${id}/respond`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Leave Balances -----------------------------------------------------------

export function useLeaveBalances(year?: number) {
  return useQuery({
    queryKey: keys.balances({ year }),
    queryFn: async () =>
      (await http.get<Page<LeaveBalance>>("/leave/balances", { params: year ? { year } : undefined })).data,
    staleTime: 60_000,
  });
}

export function useAdjustLeaveBalance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: LeaveBalanceAdjust) =>
      (await http.post<LeaveBalance>("/leave/balances/admin/adjust", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Leave Policies -----------------------------------------------------------

export function useLeavePolicies(filters?: { category?: string; employee_type?: string; is_active?: boolean }) {
  return useQuery({
    queryKey: keys.policies(filters),
    queryFn: async () =>
      (await http.get<Page<LeavePolicy>>("/leave/policies", { params: filters })).data,
    staleTime: 60_000,
  });
}

export function useCreateLeavePolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<LeavePolicy>) =>
      (await http.post<LeavePolicy>("/leave/policies", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateLeavePolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: Partial<LeavePolicy> }) =>
      (await http.patch<LeavePolicy>(`/leave/policies/${id}`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Holiday Calendar ---------------------------------------------------------

export function useHolidayCalendar(filters?: { year?: number; is_restricted?: boolean }) {
  return useQuery({
    queryKey: keys.calendar(filters),
    queryFn: async () =>
      (await http.get<Page<HolidayCalendar>>("/leave/calendar", { params: filters })).data,
    staleTime: 60_000,
  });
}

export function useCreateHoliday() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<HolidayCalendar>) =>
      (await http.post<HolidayCalendar>("/leave/calendar", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateHoliday() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: Partial<HolidayCalendar> }) =>
      (await http.patch<HolidayCalendar>(`/leave/calendar/${id}`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Offline Leave Entries ----------------------------------------------------

export function useOfflineLeaveEntries(filters?: { user_id?: number; category?: string; year?: number }) {
  return useQuery({
    queryKey: keys.offlineEntries(filters),
    queryFn: async () =>
      (await http.get<Page<OfflineLeaveEntryType>>("/leave/offline-entries", { params: filters })).data,
    staleTime: 30_000,
  });
}

export function useCreateOfflineLeaveEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<OfflineLeaveEntryType>) =>
      (await http.post<OfflineLeaveEntryType>("/leave/offline-entries", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Year End Processing ------------------------------------------------------

export function useYearEndProcessing() {
  return useMutation({
    mutationFn: async (year: number) =>
      (await http.post<{ status: string; processed_users: number; errors: unknown[] }>(
        "/leave/year-end/run",
        { year }
      )).data,
  });
}