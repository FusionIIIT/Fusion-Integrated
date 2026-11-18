/** Data access for ELM. Every mutation invalidates the whole module's keys —
 *  these pages are small and a stale approval queue is worse than a refetch. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  ApplyPayload, Holiday, LeaveApplication, LeaveBalance, Page,
} from "./types";

const KEY = "leave";

export const keys = {
  balances: (year?: string) => [KEY, "balances", year] as const,
  mine: () => [KEY, "mine"] as const,
  nominations: () => [KEY, "nominations"] as const,
  requests: () => [KEY, "requests"] as const,
  sanctions: () => [KEY, "sanctions"] as const,
  holidays: (year?: string) => [KEY, "holidays", year] as const,
};

function useInvalidate() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

export function useBalances(year?: string) {
  return useQuery({
    queryKey: keys.balances(year),
    queryFn: async () =>
      (await http.get<LeaveBalance[]>("/leave/balances", { params: { year } }))
        .data,
  });
}

export function useMyLeave() {
  return useQuery({
    queryKey: keys.mine(),
    queryFn: async () =>
      (await http.get<Page<LeaveApplication>>("/leave/applications")).data,
  });
}

export function useNominations() {
  return useQuery({
    queryKey: keys.nominations(),
    queryFn: async () =>
      (await http.get<Page<LeaveApplication>>("/leave/nominations")).data,
  });
}

export function useQueue(kind: "requests" | "sanctions") {
  return useQuery({
    queryKey: kind === "requests" ? keys.requests() : keys.sanctions(),
    queryFn: async () =>
      (await http.get<Page<LeaveApplication>>(`/leave/${kind}`)).data,
  });
}

export function useHolidays(year?: string) {
  return useQuery({
    queryKey: keys.holidays(year),
    queryFn: async () =>
      (await http.get<Holiday[]>("/leave/holidays", { params: { year } })).data,
  });
}

export function useApply() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (payload: ApplyPayload) =>
      (await http.post<LeaveApplication>("/leave/applications/apply", payload))
        .data,
    onSuccess: invalidate,
  });
}

export function useWithdraw() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async ({ id, note }: { id: number; note?: string }) =>
      (await http.post<LeaveApplication>(
        `/leave/applications/${id}/withdraw`, { note })).data,
    onSuccess: invalidate,
  });
}

export function useRequestCancellation() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async ({ id, note }: { id: number; note?: string }) =>
      (await http.post<LeaveApplication>(
        `/leave/applications/${id}/cancel`, { note })).data,
    onSuccess: invalidate,
  });
}

export function useNominationResponse() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async ({ id, accept }: { id: number; accept: boolean }) =>
      (await http.post<LeaveApplication>(
        `/leave/nominations/${id}/respond`, { accept })).data,
    onSuccess: invalidate,
  });
}

/** One hook for both decision steps: the Unit Head's review and the
 *  Sanctioning Authority's final decision take the same shape. */
export function useDecision(kind: "requests" | "sanctions") {
  const invalidate = useInvalidate();
  const path = kind === "requests" ? "review" : "decision";
  return useMutation({
    mutationFn: async ({ id, action, note }:
      { id: number; action: string; note?: string }) =>
      (await http.post<LeaveApplication>(
        `/leave/${kind}/${id}/${path}`, { action, note })).data,
    onSuccess: invalidate,
  });
}
