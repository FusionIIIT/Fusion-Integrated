/** React Query data access hooks for the ELM module. */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  ApplyLeavePayload,
  HolidayCalendar,
  LeaveBalance,
  LeaveRequest,
  LeaveTransition,
  Page,
} from "./types";

const KEY = "elm";

export const keys = {
  leaves: (filters?: Record<string, unknown>) => [KEY, "leaves", filters] as const,
  leave: (id: number) => [KEY, "leave", id] as const,
  history: (id: number) => [KEY, "history", id] as const,
  substituteRequests: () => [KEY, "substitute-requests"] as const,
  pendingApprovals: () => [KEY, "pending-approvals"] as const,
  myBalances: (year?: number) => [KEY, "my-balances", year] as const,
  userBalances: (userId: number, year?: number) => [KEY, "user-balances", userId, year] as const,
  calendar: (year?: number) => [KEY, "calendar", year] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// ── Queries ──────────────────────────────────────────────────────────────────

export function useMyLeaves(filters?: { status?: string; category?: string }) {
  return useQuery({
    queryKey: keys.leaves(filters),
    queryFn: () =>
      http.get<Page<LeaveRequest>>("/api/v1/elm/leaves", { params: filters }).then((r) => r.data),
  });
}

export function useLeaveDetail(id: number) {
  return useQuery({
    queryKey: keys.leave(id),
    queryFn: () => http.get<LeaveRequest>(`/api/v1/elm/leaves/${id}`).then((r) => r.data),
    enabled: Boolean(id),
  });
}

export function useLeaveHistory(id: number) {
  return useQuery({
    queryKey: keys.history(id),
    queryFn: () => http.get<LeaveTransition[]>(`/api/v1/elm/leaves/${id}/history`).then((r) => r.data),
    enabled: Boolean(id),
  });
}

export function useSubstituteRequests() {
  return useQuery({
    queryKey: keys.substituteRequests(),
    queryFn: () => http.get<Page<LeaveRequest>>("/api/v1/elm/substitute/requests").then((r) => r.data),
  });
}

export function usePendingApprovals() {
  return useQuery({
    queryKey: keys.pendingApprovals(),
    queryFn: () => http.get<Page<LeaveRequest>>("/api/v1/elm/approvals/pending").then((r) => r.data),
  });
}

export function useMyBalances(year?: number) {
  return useQuery({
    queryKey: keys.myBalances(year),
    queryFn: () =>
      http.get<Page<LeaveBalance>>("/api/v1/elm/balances/my", { params: { year } }).then((r) => r.data),
  });
}

export function useUserBalances(userId: number, year?: number) {
  return useQuery({
    queryKey: keys.userBalances(userId, year),
    queryFn: () =>
      http.get<Page<LeaveBalance>>(`/api/v1/elm/balances/${userId}`, { params: { year } }).then((r) => r.data),
    enabled: Boolean(userId),
  });
}

export function useHolidayCalendar(year?: number) {
  return useQuery({
    queryKey: keys.calendar(year),
    queryFn: () =>
      http.get<Page<HolidayCalendar>>("/api/v1/elm/calendar", { params: { year } }).then((r) => r.data),
  });
}

// ── Mutations ────────────────────────────────────────────────────────────────

export function useApplyLeave(options?: UseMutationOptions<LeaveRequest, unknown, ApplyLeavePayload>) {
  const qc = useQueryClient();
  return useMutation({
    ...options,
    mutationFn: (payload: ApplyLeavePayload) =>
      http.post<LeaveRequest>("/api/v1/elm/leaves", payload).then((r) => r.data),
    onSuccess: (...args) => {
      invalidateAll(qc);
      options?.onSuccess?.(...args);
    },
  });
}

export function useWithdrawLeave(options?: UseMutationOptions<LeaveRequest, unknown, { id: number; reason?: string }>) {
  const qc = useQueryClient();
  return useMutation({
    ...options,
    mutationFn: ({ id, reason }) =>
      http.delete<LeaveRequest>(`/api/v1/elm/leaves/${id}`, { data: { reason } }).then((r) => r.data),
    onSuccess: (...args) => {
      invalidateAll(qc);
      options?.onSuccess?.(...args);
    },
  });
}

export function useRespondSubstitute(
  options?: UseMutationOptions<LeaveRequest, unknown, { id: number; accept: boolean; reason?: string }>
) {
  const qc = useQueryClient();
  return useMutation({
    ...options,
    mutationFn: ({ id, accept, reason }) =>
      http.post<LeaveRequest>(`/api/v1/elm/leaves/${id}/substitute`, { accept, reason }).then((r) => r.data),
    onSuccess: (...args) => {
      invalidateAll(qc);
      options?.onSuccess?.(...args);
    },
  });
}

export function useUnitHeadReview(
  options?: UseMutationOptions<LeaveRequest, unknown, { id: number; action: string; reason?: string }>
) {
  const qc = useQueryClient();
  return useMutation({
    ...options,
    mutationFn: ({ id, action, reason }) =>
      http.post<LeaveRequest>(`/api/v1/elm/leaves/${id}/review`, { action, reason }).then((r) => r.data),
    onSuccess: (...args) => {
      invalidateAll(qc);
      options?.onSuccess?.(...args);
    },
  });
}

export function useSanctionDecision(
  options?: UseMutationOptions<LeaveRequest, unknown, { id: number; approve: boolean; reason?: string }>
) {
  const qc = useQueryClient();
  return useMutation({
    ...options,
    mutationFn: ({ id, approve, reason }) =>
      http.post<LeaveRequest>(`/api/v1/elm/leaves/${id}/sanction`, { approve, reason }).then((r) => r.data),
    onSuccess: (...args) => {
      invalidateAll(qc);
      options?.onSuccess?.(...args);
    },
  });
}

export function useCancelRequest(
  options?: UseMutationOptions<LeaveRequest, unknown, { id: number; reason?: string }>
) {
  const qc = useQueryClient();
  return useMutation({
    ...options,
    mutationFn: ({ id, reason }) =>
      http.post<LeaveRequest>(`/api/v1/elm/leaves/${id}/cancel`, { reason }).then((r) => r.data),
    onSuccess: (...args) => {
      invalidateAll(qc);
      options?.onSuccess?.(...args);
    },
  });
}

export function useCancelDecision(
  options?: UseMutationOptions<LeaveRequest, unknown, { id: number; approve: boolean; reason?: string }>
) {
  const qc = useQueryClient();
  return useMutation({
    ...options,
    mutationFn: ({ id, approve, reason }) =>
      http.post<LeaveRequest>(`/api/v1/elm/leaves/${id}/cancel/decide`, { approve, reason }).then((r) => r.data),
    onSuccess: (...args) => {
      invalidateAll(qc);
      options?.onSuccess?.(...args);
    },
  });
}

export function useExtensionRequest(
  options?: UseMutationOptions<LeaveRequest, unknown, { id: number; new_end_date: string; reason?: string }>
) {
  const qc = useQueryClient();
  return useMutation({
    ...options,
    mutationFn: ({ id, new_end_date, reason }) =>
      http.post<LeaveRequest>(`/api/v1/elm/leaves/${id}/extend`, { new_end_date, reason }).then((r) => r.data),
    onSuccess: (...args) => {
      invalidateAll(qc);
      options?.onSuccess?.(...args);
    },
  });
}

export function useExtensionDecision(
  options?: UseMutationOptions<LeaveRequest, unknown, { id: number; approve: boolean; new_end_date?: string; reason?: string }>
) {
  const qc = useQueryClient();
  return useMutation({
    ...options,
    mutationFn: ({ id, approve, new_end_date, reason }) =>
      http.post<LeaveRequest>(`/api/v1/elm/leaves/${id}/extend/decide`, { approve, new_end_date, reason }).then((r) => r.data),
    onSuccess: (...args) => {
      invalidateAll(qc);
      options?.onSuccess?.(...args);
    },
  });
}

export function useResumptionRequest(
  options?: UseMutationOptions<LeaveRequest, unknown, { id: number; resumption_date: string; reason?: string }>
) {
  const qc = useQueryClient();
  return useMutation({
    ...options,
    mutationFn: ({ id, resumption_date, reason }) =>
      http.post<LeaveRequest>(`/api/v1/elm/leaves/${id}/resume`, { resumption_date, reason }).then((r) => r.data),
    onSuccess: (...args) => {
      invalidateAll(qc);
      options?.onSuccess?.(...args);
    },
  });
}

export function useResumptionReview(
  options?: UseMutationOptions<LeaveRequest, unknown, { id: number; reason?: string }>
) {
  const qc = useQueryClient();
  return useMutation({
    ...options,
    mutationFn: ({ id, reason }) =>
      http.post<LeaveRequest>(`/api/v1/elm/leaves/${id}/resume/review`, { reason }).then((r) => r.data),
    onSuccess: (...args) => {
      invalidateAll(qc);
      options?.onSuccess?.(...args);
    },
  });
}

export function useRecordOffline(
  options?: UseMutationOptions<LeaveRequest, unknown, {
    target_user_id: number;
    category: string;
    start_date: string;
    end_date: string;
    offline_reference: string;
    purpose?: string;
    half?: string;
  }>
) {
  const qc = useQueryClient();
  return useMutation({
    ...options,
    mutationFn: (payload) =>
      http.post<LeaveRequest>("/api/v1/elm/offline", payload).then((r) => r.data),
    onSuccess: (...args) => {
      invalidateAll(qc);
      options?.onSuccess?.(...args);
    },
  });
}
