import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../lib/http";
import type {
  DecideLeaveInput,
  LeaveBalance,
  LeaveRequest,
  SubmitLeaveInput,
} from "./types";

export function useMyLeaves() {
  return useQuery({
    queryKey: ["leave", "mine"],
    queryFn: async () => {
      const { data } = await http.get<LeaveRequest[]>("/leave/requests/");
      return data;
    },
  });
}

export function useMyBalances() {
  return useQuery({
    queryKey: ["leave", "balances"],
    queryFn: async () => {
      const { data } = await http.get<LeaveBalance[]>("/leave/balances/");
      return data;
    },
  });
}

export function usePendingApprovals() {
  return useQuery({
    queryKey: ["leave", "pending"],
    queryFn: async () => {
      const { data } = await http.get<LeaveRequest[]>("/leave/pending/");
      return data;
    },
  });
}

export function useSubmitLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SubmitLeaveInput) => {
      const { data } = await http.post<LeaveRequest>("/leave/requests/", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave", "mine"] });
      qc.invalidateQueries({ queryKey: ["leave", "balances"] });
    },
  });
}

export function useDecideLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: DecideLeaveInput & { id: number }) => {
      const { data } = await http.post(`/leave/requests/${id}/decide/`, payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave", "pending"] });
      qc.invalidateQueries({ queryKey: ["leave", "mine"] });
      qc.invalidateQueries({ queryKey: ["leave", "balances"] });
    },
  });
}

export function useCancelLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason?: string }) => {
      const { data } = await http.post(`/leave/requests/${id}/cancel/`, { reason });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave", "mine"] });
      qc.invalidateQueries({ queryKey: ["leave", "pending"] });
      qc.invalidateQueries({ queryKey: ["leave", "balances"] });
    },
  });
}
