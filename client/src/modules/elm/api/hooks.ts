import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type { Holiday, LeaveApplication, LeaveBalance, Page } from "./types";

const KEY = "elm";

export const keys = {
  applications: () => [KEY, "applications"] as const,
  balances: () => [KEY, "balances"] as const,
  inbox: () => [KEY, "inbox"] as const,
  holidays: () => [KEY, "holidays"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

export function useApplications() {
  return useQuery({
    queryKey: keys.applications(),
    queryFn: async () =>
      (await http.get<Page<LeaveApplication>>("/leave/applications")).data,
    staleTime: 15_000,
  });
}

export function useApply() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<LeaveApplication>("/leave/applications", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdraw() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveApplication>(`/leave/applications/${id}/withdraw`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCancel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveApplication>(`/leave/applications/${id}/cancel`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useBalances() {
  return useQuery({
    queryKey: keys.balances(),
    queryFn: async () =>
      (await http.get<Page<LeaveBalance>>("/leave/balances")).data,
    staleTime: 60_000,
  });
}

export function useInbox() {
  return useQuery({
    queryKey: keys.inbox(),
    queryFn: async () =>
      (await http.get<Page<LeaveApplication>>("/leave/inbox")).data,
    staleTime: 15_000,
  });
}

export function useDecide() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, approve }: { id: number; approve: boolean }) =>
      (await http.post<LeaveApplication>(`/leave/applications/${id}/decide`,
                                         { approve })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubstituteRespond() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, accept }: { id: number; accept: boolean }) =>
      (await http.post<LeaveApplication>(`/leave/substitute/${id}/respond`,
                                         { accept })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useHolidays() {
  return useQuery({
    queryKey: keys.holidays(),
    queryFn: async () =>
      (await http.get<Page<Holiday>>("/leave/holidays")).data,
    staleTime: 60_000,
  });
}

export function useAddHoliday() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<Holiday>("/leave/holidays", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}
