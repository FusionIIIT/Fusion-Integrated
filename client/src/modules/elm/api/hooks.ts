/** Typed data access for the ELM module. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  LeaveApplicationCreateRequest,
  LeaveApplicationCreateResponse,
  LeaveBalance,
  LeaveCategory,
  LeaveHistoryEntry,
  ApprovalRouting,
  ApprovalDecisionRequest,
  LeaveApplication,
  PrintApplicationResponse,
  SLAThresholdConfig,
  YearEndProcessingResult,
} from "./types";

const KEY = "elm";

export const keys = {
  leaveCategories: () => [KEY, "categories"] as const,
  balances: () => [KEY, "balances"] as const,
  history: () => [KEY, "history"] as const,
  print: (appPk: number) => [KEY, "print", appPk] as const,
  slaThresholds: () => [KEY, "sla", "thresholds"] as const,
};

export function useLeaveCategories() {
  return useQuery({
    queryKey: keys.leaveCategories(),
    queryFn: async () =>
      (await http.get<LeaveCategory[]>("/elm/categories")).data,
    staleTime: 300_000,
  });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: keys.balances(),
    queryFn: async () =>
      (await http.get<{ balances: LeaveBalance[] }>("/elm/balances")).data,
    staleTime: 120_000,
  });
}

export function useLeaveHistory() {
  return useQuery({
    queryKey: keys.history(),
    queryFn: async () =>
      (await http.get<LeaveHistoryEntry[]>("/elm/history")).data,
    staleTime: 120_000,
  });
}

export function useSubmitLeaveApplication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: LeaveApplicationCreateRequest) =>
      (await http.post<LeaveApplicationCreateResponse>("/elm/apply", payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [KEY] }),
  });
}

export function usePrintApplication(appPk: number) {
  return useQuery({
    queryKey: keys.print(appPk),
    queryFn: async () =>
      (await http.get<PrintApplicationResponse>(
        "/elm/application/" + appPk + "/print",
      )).data,
    enabled: appPk > 0,
  });
}

export function useSLAThresholds() {
  return useQuery({
    queryKey: keys.slaThresholds(),
    queryFn: async () =>
      (await http.get<SLAThresholdConfig>("/elm/sla/thresholds")).data,
  });
}

export function useSaveSLAThresholds() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SLAThresholdConfig) =>
      (await http.post<SLAThresholdConfig>("/elm/sla/thresholds", payload)).data,
    onSuccess: () => queryClient.invalidateQueries({
      queryKey: keys.slaThresholds(),
    }),
  });
}

export function useYearEndProcessing() {
  return useMutation({
    mutationFn: async () =>
      (await http.post<YearEndProcessingResult>("/elm/year-end")).data,
  });
}


export function useApprovalQueue() {
  return useQuery({
    queryKey: [KEY, "workflow", "queue"],
    queryFn: async () =>
      (await http.get<LeaveApplication[]>("/elm/workflow/queue")).data,
    refetchInterval: 30_000,
  });
}

export function useApprovalDecision() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ pk, ...payload }: ApprovalDecisionRequest & { pk: number }) =>
      (await http.post<LeaveApplication>("/elm/workflow/decision/" + pk, payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [KEY, "workflow"] }),
  });
}

export function useApprovalRouting() {
  return useQuery({
    queryKey: [KEY, "workflow", "routing"],
    queryFn: async () =>
      (await http.get<ApprovalRouting[]>("/elm/workflow/routing")).data,
  });
}

export function useSaveApprovalRouting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Omit<ApprovalRouting, "configured">) =>
      (await http.post<ApprovalRouting>("/elm/workflow/routing", payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [KEY, "workflow", "routing"] }),
  });
}
