/** Data access for the leave module.
 *
 *  Every mutation invalidates the keys it can affect — a balance shown next to
 *  an approved request is the value the ledger just moved. */
import {
  useMutation, useQuery, useQueryClient, type UseMutationOptions,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Balance, Holiday, LeaveApplication, LeaveEvent, LeaveType, Page,
  SubmitLeavePayload,
} from "./types";

const KEY = "elm";

export const keys = {
  types: () => [KEY, "types"] as const,
  holidays: (range?: unknown) => [KEY, "holidays", range] as const,
  applications: (filters?: unknown) => [KEY, "applications", filters] as const,
  approvals: () => [KEY, "approvals"] as const,
  balances: (userId?: number, year?: number) =>
    [KEY, "balances", userId, year] as const,
  history: (id: number) => [KEY, "history", id] as const,
};

/** Coarse on purpose — these screens are small, and correctness beats shaving
 *  a refetch. */
function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Configuration -------------------------------------------------------------
export function useLeaveTypes() {
  return useQuery({
    queryKey: keys.types(),
    queryFn: async () => (await http.get<LeaveType[]>("/elm/types")).data,
    staleTime: 5 * 60_000,
  });
}

export function useHolidays(range?: { from?: string; to?: string }) {
  return useQuery({
    queryKey: keys.holidays(range),
    queryFn: async () =>
      (await http.get<Holiday[]>("/elm/holidays", { params: range })).data,
    staleTime: 5 * 60_000,
  });
}

// -- Applications --------------------------------------------------------------
export function useMyApplications(filters?: { status?: string }) {
  return useQuery({
    queryKey: keys.applications(filters),
    queryFn: async () =>
      (await http.get<Page<LeaveApplication>>("/elm/applications",
        { params: filters })).data,
    staleTime: 15_000,
  });
}

export function useApprovals() {
  return useQuery({
    queryKey: keys.approvals(),
    queryFn: async () =>
      (await http.get<Page<LeaveApplication>>("/elm/approvals")).data,
    staleTime: 15_000,
  });
}

export function useHistory(id: number | null) {
  return useQuery({
    queryKey: keys.history(id ?? 0),
    queryFn: async () =>
      (await http.get<LeaveEvent[]>(`/elm/applications/${id}/history`)).data,
    enabled: id !== null,
  });
}

export function useSubmitLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SubmitLeavePayload) =>
      (await http.post<LeaveApplication>("/elm/applications/submit", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useTransition(
  options?: UseMutationOptions<LeaveApplication, unknown,
    { id: number; to_status: string; note?: string }>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, to_status, note }: {
      id: number; to_status: string; note?: string;
    }) => (await http.post<LeaveApplication>(
      `/elm/applications/${id}/transition`, { to_status, note: note ?? "" })).data,
    onSuccess: () => invalidateAll(qc),
    ...options,
  });
}

// -- Balances ------------------------------------------------------------------
export function useBalances(userId?: number, year?: number) {
  return useQuery({
    queryKey: keys.balances(userId, year),
    queryFn: async () =>
      (await http.get<Balance[]>("/elm/balances",
        { params: { user_id: userId, year } })).data,
    staleTime: 30_000,
  });
}

export function useGrantBalance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      user_id: number; leave_type_id: number; year: number;
      days: string; note: string;
    }) => (await http.post("/elm/balances/grant", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Setup ---------------------------------------------------------------------
export function useCreateLeaveType() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await http.post<LeaveType>("/elm/types/create", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSetLeaveTypeActive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action }: { id: number; action: "activate" | "deactivate" }) =>
      (await http.post<LeaveType>(`/elm/types/${id}/${action}`, {})).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCreateHoliday() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { date: string; name: string }) =>
      (await http.post<Holiday>("/elm/holidays/create", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteHoliday() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.delete(`/elm/holidays/${id}`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}
