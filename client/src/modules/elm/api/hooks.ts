import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Holiday,
  LeaveApplication,
  LeaveBalance,
  Page,
  VacationPeriod,
} from "./types";

const KEY = "elm";

export const keys = {
  applications: () => [KEY, "applications"] as const,
  balances: () => [KEY, "balances"] as const,
  inbox: () => [KEY, "inbox"] as const,
  substituteInbox: () => [KEY, "substitute-inbox"] as const,
  holidays: () => [KEY, "holidays"] as const,
  vacations: () => [KEY, "vacations"] as const,
  printable: (id: number) => [KEY, "printable", id] as const,
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
    mutationFn: async ({ id, reason }: { id: number; reason?: string }) =>
      (await http.post<LeaveApplication>(`/leave/applications/${id}/cancel`, { reason })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDecideCancellation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, approve, note }: { id: number; approve: boolean; note?: string }) =>
      (await http.post<LeaveApplication>(`/leave/applications/${id}/decide-cancellation`, {
        approve,
        note,
      })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      actual_resumption_date,
      note,
    }: {
      id: number;
      actual_resumption_date: string;
      note?: string;
    }) =>
      (await http.post<LeaveApplication>(`/leave/applications/${id}/resume`, {
        actual_resumption_date,
        note,
      })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReviewResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, note }: { id: number; note?: string }) =>
      (await http.post<LeaveApplication>(`/leave/applications/${id}/review-resumption`, {
        note,
      })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRenominateSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, substitute_user_id }: { id: number; substitute_user_id: number }) =>
      (await http.post<LeaveApplication>(`/leave/applications/${id}/renominate-substitute`, {
        substitute_user_id,
      })).data,
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

export function useSubstituteInbox() {
  return useQuery({
    queryKey: keys.substituteInbox(),
    queryFn: async () =>
      (await http.get<Page<LeaveApplication>>("/leave/substitute-inbox")).data,
    staleTime: 15_000,
  });
}

export function useRecommend() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      recommended,
      note,
    }: {
      id: number;
      recommended: boolean;
      note?: string;
    }) =>
      (await http.post<LeaveApplication>(`/leave/applications/${id}/recommend`, {
        recommended,
        note,
      })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDecide() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, approve, note }: { id: number; approve: boolean; note?: string }) =>
      (await http.post<LeaveApplication>(`/leave/applications/${id}/decide`, {
        approve,
        note,
      })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubstituteRespond() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, accept }: { id: number; accept: boolean }) =>
      (await http.post<LeaveApplication>(`/leave/substitute/${id}/respond`, {
        accept,
      })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRecordOffline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await http.post<LeaveApplication>("/leave/offline", payload)).data,
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

export function useVacations() {
  return useQuery({
    queryKey: keys.vacations(),
    queryFn: async () =>
      (await http.get<Page<VacationPeriod>>("/leave/vacations")).data,
    staleTime: 60_000,
  });
}

export function useAddVacation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<VacationPeriod>("/leave/vacations", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePrintable(id: number | null) {
  return useQuery({
    queryKey: keys.printable(id ?? 0),
    queryFn: async () => {
      if (!id) return null;
      return (await http.get<Record<string, unknown>>(`/leave/applications/${id}/printable`)).data;
    },
    enabled: Boolean(id),
  });
}
