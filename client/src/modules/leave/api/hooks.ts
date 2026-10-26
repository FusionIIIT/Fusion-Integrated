/** Data access for the leave module; every mutation invalidates the leave cache. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type { Holiday, LeaveBalance, LeaveRequest, Page } from "./types";

const KEY = "leave";

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

/** A mutation that POSTs to `url(args)` and refreshes everything leave shows. */
function usePost<A, R = LeaveRequest>(url: (args: A) => string, body: (args: A) => unknown) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: A) => (await http.post<R>(url(args), body(args))).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Requests ------------------------------------------------------------------
export function useRequests() {
  return useQuery({
    queryKey: [KEY, "requests"],
    queryFn: async () => (await http.get<Page<LeaveRequest>>("/leave/requests")).data,
    staleTime: 30_000,
  });
}

export const useApply = () =>
  usePost<Record<string, unknown>>(() => "/leave/requests", (body) => body);

export const useWithdraw = () =>
  usePost<number>((id) => `/leave/requests/${id}/withdraw`, () => ({}));

export const useCancel = () =>
  usePost<number>((id) => `/leave/requests/${id}/cancel`, () => ({}));

export const useSubstituteResponse = () =>
  usePost<{ id: number; accept: boolean }>(
    ({ id }) => `/leave/requests/${id}/substitute-response`, ({ accept }) => ({ accept }));

export const useReview = () =>
  usePost<{ id: number; outcome: string; note: string }>(
    ({ id }) => `/leave/requests/${id}/review`, ({ outcome, note }) => ({ outcome, note }));

export const useRoute = () =>
  usePost<{ id: number; note: string }>(
    ({ id }) => `/leave/requests/${id}/route`, ({ note }) => ({ note }));

export const useSanction = () =>
  usePost<{ id: number; decision: string; note: string }>(
    ({ id }) => `/leave/requests/${id}/sanction`, ({ decision, note }) => ({ decision, note }));

// -- Balances and calendar -----------------------------------------------------
export function useBalances() {
  return useQuery({
    queryKey: [KEY, "balances"],
    queryFn: async () => (await http.get<LeaveBalance[]>("/leave/balances")).data,
    staleTime: 30_000,
  });
}

export function useHolidays() {
  return useQuery({
    queryKey: [KEY, "holidays"],
    queryFn: async () => (await http.get<Page<Holiday>>("/leave/holidays")).data,
    staleTime: 60_000,
  });
}

export const useAddHoliday = () =>
  usePost<Record<string, unknown>, Holiday>(() => "/leave/holidays", (body) => body);
