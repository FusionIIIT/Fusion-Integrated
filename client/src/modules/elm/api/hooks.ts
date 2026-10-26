import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  ApplyLeavePayload,
  LeaveApplication,
  LeaveBalance,
} from "./types";

const KEY = "elm";

export const keys = {
  balances: () => [KEY, "balances"] as const,
  myLeaves: () => [KEY, "my-leaves"] as const,
  approvals: () => [KEY, "approvals"] as const,
  substitutes: () => [KEY, "substitutes"] as const,
};

export function useLeaveBalances() {
  return useQuery({
    queryKey: keys.balances(),
    queryFn: async () => {
      const res = await http.get<LeaveBalance[]>("/api/v1/elm/balances/");
      return res.data;
    },
  });
}

export function useMyLeaves() {
  return useQuery({
    queryKey: keys.myLeaves(),
    queryFn: async () => {
      const res = await http.get<LeaveApplication[]>("/api/v1/elm/applications/");
      return res.data;
    },
  });
}

export function useApplyLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ApplyLeavePayload) => {
      const res = await http.post<LeaveApplication>("/api/v1/elm/applications/", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useWithdrawLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await http.post<LeaveApplication>(`/api/v1/elm/applications/${id}/withdraw/`);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useCancelLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason?: string }) => {
      const res = await http.post<LeaveApplication>(
        `/api/v1/elm/applications/${id}/cancel/`,
        { reason }
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useReplaceSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, substitute_id }: { id: number; substitute_id: number }) => {
      const res = await http.post<LeaveApplication>(
        `/api/v1/elm/applications/${id}/substitute/`,
        { substitute_id }
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useApprovals() {
  return useQuery({
    queryKey: keys.approvals(),
    queryFn: async () => {
      const res = await http.get<LeaveApplication[]>("/api/v1/elm/approvals/");
      return res.data;
    },
  });
}

export function useApprovalAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, comments }: { id: number; action: string; comments?: string }) => {
      const res = await http.post<LeaveApplication>(`/api/v1/elm/approvals/${id}/action/`, { action, comments });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useSubstituteRequests() {
  return useQuery({
    queryKey: keys.substitutes(),
    queryFn: async () => {
      const res = await http.get<LeaveApplication[]>("/api/v1/elm/substitutes/");
      return res.data;
    },
  });
}

export function useSubstituteAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, comments }: { id: number; action: "accept" | "decline"; comments?: string }) => {
      const res = await http.post<LeaveApplication>(`/api/v1/elm/substitutes/${id}/action/`, { action, comments });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}
