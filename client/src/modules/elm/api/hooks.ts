/** Data access for the ELM module. */

import {
  useMutation, useQuery, useQueryClient, type UseMutationOptions,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  LeaveCategory, LeaveBalance, LeaveApplication,
  LeaveApplicationCreateRequest, LeaveApplicationCreateResponse,
  LeaveBalancesResponse, LeaveHistoryEntry,
  PrintApplicationRequest, PrintApplicationResponse,
  SLAThresholdConfig, YearEndProcessingResult,
} from "./types";

const KEY = "elm";

export const keys = {
  leaveCategories: () => [KEY, "categories"] as const,
  balances: (userId?: number) => [KEY, "balances", userId] as const,
  history: (userId?: number) => [KEY, "history", userId] as const,
  print: (appPk: number) => [KEY, "print", appPk] as const,
  slaThresholds: () => [KEY, "sla", "thresholds"] as const,
  yearEnd: () => [KEY, "year-end"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Leave Categories --------------------------------------------------------

export function useLeaveCategories() {
  return useQuery({
    queryKey: keys.leaveCategories(),
    queryFn: async () =>
      (await http.get<LeaveCategory[]>("/api/v1/elm/categories")).data,
    staleTime: 300_000,
  });
}

// -- Leave Balances ----------------------------------------------------------

export function useLeaveBalances(userId?: number) {
  return useQuery({
    queryKey: keys.balances(userId),
    queryFn: async () =>
      (await http.get<LeaveBalancesResponse>(
        `/api/v1/elm/balances?user_id=${userId || ""}`)).data,
    staleTime: 120_000,
  });
}

// -- Leave History -----------------------------------------------------------

export function useLeaveHistory(userId?: number) {
  return useQuery({
    queryKey: keys.history(userId),
    queryFn: async () =>
      (await http.get<LeaveHistoryEntry[]>(
        `/api/v1/elm/history?user_id=${userId || ""}`)).data,
    staleTime: 120_000,
  });
}

// -- Print Application -------------------------------------------------------

export function usePrintApplication(appPk: number) {
  return useQuery({
    queryKey: keys.print(appPk),
    queryFn: async () =>
      (await http.get<PrintApplicationResponse>(
        `/api/v1/elm/application/${appPk}/print`)).data,
    enabled: appPk > 0,
  });
}

// -- SLA Thresholds --------------------------------------------------------

export function useSLATrusts() {
  return useQuery({
    queryKey: keys.slaThresholds(),
    queryFn: async () =>
      (await http.get<SLAThresholdConfig>(
        "/api/v1/elm/sla/thresholds")).data,
    staleTime: 300_000,
  });
}

// -- Year-End Processing -----------------------------------------------------

export function useYearEndProcessing() {
  return useMutation({
    mutationFn: async () =>
      (await http.post<YearEndProcessingResult>(
        "/api/v1/elm/year-end")).data,
  });
}