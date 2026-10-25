import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  LeaveApplicationDetail,
  LeaveApplicationItem,
  LeaveApplyPayload,
  LeaveBalance,
  LeaveCategory,
  SubstitutePayload,
  TransitionPayload,
  WithdrawPayload,
} from "./types";

export function useLeaveCategories() {
  return useQuery({
    queryKey: ["elm", "categories"],
    queryFn: async () => {
      const res = await http.get<LeaveCategory[]>("/elm/categories");
      return res.data;
    },
  });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: ["elm", "balances"],
    queryFn: async () => {
      const res = await http.get<LeaveBalance[]>("/elm/balances");
      return res.data;
    },
  });
}

export function useMyApplications() {
  return useQuery({
    queryKey: ["elm", "applications"],
    queryFn: async () => {
      const res = await http.get<LeaveApplicationItem[]>("/elm/applications");
      return res.data;
    },
  });
}

export function useApplicationDetail(id: number | null) {
  return useQuery({
    queryKey: ["elm", "application", id],
    queryFn: async () => {
      if (!id) return null;
      const res = await http.get<LeaveApplicationDetail>(`/elm/applications/${id}`);
      return res.data;
    },
    enabled: Boolean(id),
  });
}

export function usePendingApprovals() {
  return useQuery({
    queryKey: ["elm", "approvals"],
    queryFn: async () => {
      const res = await http.get<LeaveApplicationItem[]>("/elm/approvals");
      return res.data;
    },
  });
}

export function useApplyLeave() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: LeaveApplyPayload) => {
      const res = await http.post<LeaveApplicationDetail>("/elm/applications", payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["elm"] });
    },
  });
}

export function useWithdrawLeave() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: WithdrawPayload }) => {
      const res = await http.post<LeaveApplicationDetail>(
        `/elm/applications/${id}/withdraw`,
        payload
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["elm"] });
    },
  });
}

export function useSubstituteResponse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: SubstitutePayload }) => {
      const res = await http.post<LeaveApplicationDetail>(
        `/elm/applications/${id}/substitute`,
        payload
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["elm"] });
    },
  });
}

export function useTransitionLeave() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: TransitionPayload }) => {
      const res = await http.post<LeaveApplicationDetail>(
        `/elm/applications/${id}/transition`,
        payload
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["elm"] });
    },
  });
}
