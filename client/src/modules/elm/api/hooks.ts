import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  ApplyLeavePayload,
  Holiday,
  LeaveApplication,
  LeaveBalance,
  ReviewLeavePayload,
} from "./types";

const KEY = "elm";

export const keys = {
  balances: () => [KEY, "balances"] as const,
  myLeaves: () => [KEY, "my-leaves"] as const,
  approvals: () => [KEY, "approvals"] as const,
  holidays: () => [KEY, "holidays"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

export function useBalances() {
  return useQuery({
    queryKey: keys.balances(),
    queryFn: async () => (await http.get<LeaveBalance[]>("/elm/balances/")).data,
    staleTime: 30_000,
  });
}

export function useMyLeaves() {
  return useQuery({
    queryKey: keys.myLeaves(),
    queryFn: async () => (await http.get<LeaveApplication[]>("/elm/applications/")).data,
    staleTime: 30_000,
  });
}

export function useApprovalQueue() {
  return useQuery({
    queryKey: keys.approvals(),
    queryFn: async () => (await http.get<LeaveApplication[]>("/elm/approvals/")).data,
    staleTime: 30_000,
  });
}

export function useHolidays() {
  return useQuery({
    queryKey: keys.holidays(),
    queryFn: async () => (await http.get<Holiday[]>("/elm/holidays/")).data,
    staleTime: 60_000,
  });
}

export function useApplyLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ApplyLeavePayload) =>
      (await http.post<LeaveApplication>("/elm/applications/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCancelLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveApplication>(`/elm/applications/${id}/cancel/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReviewLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, remarks }: ReviewLeavePayload) =>
      (await http.post<LeaveApplication>(`/elm/applications/${id}/review/`, { action, remarks })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

