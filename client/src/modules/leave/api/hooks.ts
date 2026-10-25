import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http, errorMessage } from "../../../lib/http";
import type {
  LeaveBalance, LeaveRequest, LeaveResumption, LeaveType,
} from "./types";

const KEY = "leave";

export const keys = {
  types: () => [KEY, "types"] as const,
  balances: () => [KEY, "balances"] as const,
  requests: () => [KEY, "requests"] as const,
  approvals: () => [KEY, "approvals"] as const,
  resumptions: (id?: number) => [KEY, "resumptions", id] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

export function useLeaveTypes() {
  return useQuery({
    queryKey: keys.types(),
    queryFn: async () => (await http.get<LeaveType[]>("/leave/types")).data,
    staleTime: 60_000,
  });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: keys.balances(),
    queryFn: async () => (await http.get<LeaveBalance[]>("/leave/balances")).data,
    staleTime: 30_000,
  });
}

export function useLeaveRequests() {
  return useQuery({
    queryKey: keys.requests(),
    queryFn: async () => (await http.get<LeaveRequest[]>("/leave/requests")).data,
    staleTime: 15_000,
  });
}

export function usePendingApprovals() {
  return useQuery({
    queryKey: keys.approvals(),
    queryFn: async () => (await http.get<LeaveRequest[]>("/leave/approvals")).data,
    staleTime: 15_000,
  });
}

export function useCreateLeaveRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<LeaveRequest>) =>
      (await http.post<LeaveRequest>("/leave/requests", data)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCancelLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/cancel`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdrawLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/withdraw`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useApproveLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remarks }: { id: number; remarks?: string }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/decision`, {
        action: "approve", remarks,
      })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRejectLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remarks }: { id: number; remarks?: string }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/decision`, {
        action: "reject", remarks,
      })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAllocateBalance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      user_id: number; leave_type: number; year?: number; allocated_days: number | string;
    }) => (await http.post<LeaveBalance>("/leave/balances/allocate", data)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useNominateSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, substitute_user_id }: { id: number; substitute_user_id: number }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/substitute`, { substitute_user_id })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubstituteResponse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action }: { id: number; action: "accept" | "decline" }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/substitute-response`, { action })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReviewLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action }: { id: number; action: "recommend" | "not_recommend" }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/review`, { action })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useExtendLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...data }: { id: number } & Record<string, unknown>) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/extend`, data)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...data }: { id: number } & Record<string, unknown>) =>
      (await http.post<LeaveResumption>(`/leave/requests/${id}/resumption`, data)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReviewResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...data }: { id: number } & Record<string, unknown>) =>
      (await http.post<LeaveResumption>(`/leave/resumptions/${id}/review`, data)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export { errorMessage };