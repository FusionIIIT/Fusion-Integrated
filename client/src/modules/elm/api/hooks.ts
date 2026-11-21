import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type { ApplyLeavePayload, LeaveBalance, LeaveRequest } from "./types";

export function useLeaveCatalog() {
  return useQuery({
    queryKey: ["elm", "catalog"],
    queryFn: async () => (await http.get<{ entitlements: Record<string, string> }>("/elm/catalog")).data,
  });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: ["elm", "balances"],
    queryFn: async () => (await http.get<LeaveBalance[]>("/elm/balances")).data,
  });
}

export function useMyLeaveRequests() {
  return useQuery({
    queryKey: ["elm", "requests"],
    queryFn: async () => (await http.get<LeaveRequest[]>("/elm/requests")).data,
  });
}

export function useApplyLeave() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ApplyLeavePayload) =>
      (await http.post<LeaveRequest>("/elm/requests", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["elm", "requests"] });
      queryClient.invalidateQueries({ queryKey: ["elm", "balances"] });
    },
  });
}

export function useWithdrawLeave() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (requestId: number) =>
      (await http.post<LeaveRequest>(`/elm/requests/${requestId}/withdraw`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["elm", "requests"] });
    },
  });
}

export function useCancelLeave() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (requestId: number) =>
      (await http.post<LeaveRequest>(`/elm/requests/${requestId}/cancel`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["elm", "requests"] });
      queryClient.invalidateQueries({ queryKey: ["elm", "balances"] });
    },
  });
}

export function useSubstituteTasks() {
  return useQuery({
    queryKey: ["elm", "tasks", "substitute"],
    queryFn: async () => (await http.get<LeaveRequest[]>("/elm/tasks/substitute")).data,
  });
}

export function useRespondSubstitute() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ requestId, action, remarks }: { requestId: number; action: "accept" | "decline"; remarks?: string }) =>
      (await http.post(`/elm/tasks/substitute/${requestId}/respond`, { action, remarks })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["elm", "tasks", "substitute"] });
    },
  });
}

export function useReviewTasks() {
  return useQuery({
    queryKey: ["elm", "tasks", "review"],
    queryFn: async () => (await http.get<LeaveRequest[]>("/elm/tasks/review")).data,
  });
}

export function useReviewDecision() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ requestId, action, reason }: { requestId: number; action: "approve" | "reject" | "recommend"; reason?: string }) =>
      (await http.post(`/elm/tasks/review/${requestId}/decision`, { action, reason })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["elm", "tasks", "review"] });
      queryClient.invalidateQueries({ queryKey: ["elm", "balances"] });
    },
  });
}
