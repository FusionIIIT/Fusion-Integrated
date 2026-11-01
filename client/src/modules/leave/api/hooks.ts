/** Data access for ELM. Every mutation invalidates the whole module's cache. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  ApplyInput, AuthorityRule, Balance, Employee, HolidayCalendar, LeaveRequest, Page,
  Policy, Resumption, Unit,
} from "./types";

const KEY = "leave";

function useLeaveMutation<V>(fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}

export function useBalances(year: number) {
  return useQuery({
    queryKey: [KEY, "balances", year],
    queryFn: async () => (await http.get<{ year: number; results: Balance[] }>(
      "/leave/me/balances", { params: { year } })).data,
  });
}

export function useMyRequests() {
  return useQuery({
    queryKey: [KEY, "mine"],
    queryFn: async () => (await http.get<Page<LeaveRequest>>(
      "/leave/requests", { params: { mine: 1, limit: 100 } })).data,
  });
}

export function useRequest(id: number | null) {
  return useQuery({
    queryKey: [KEY, "request", id],
    enabled: id !== null,
    queryFn: async () => (await http.get<LeaveRequest>(`/leave/requests/${id}`)).data,
  });
}

export function useTasks() {
  return useQuery({
    queryKey: [KEY, "tasks"],
    queryFn: async () => (await http.get<{
      requests: LeaveRequest[]; resumptions: Resumption[] }>("/leave/tasks")).data,
  });
}

export function useEmployees(q: string) {
  return useQuery({
    queryKey: [KEY, "employees", q],
    queryFn: async () => (await http.get<{ results: Employee[] }>(
      "/leave/employees", { params: { q } })).data.results,
    staleTime: 60_000,
  });
}

export function useApply() {
  return useLeaveMutation((body: ApplyInput) => http.post("/leave/requests/apply", body));
}

/** One hook for every POST /requests/:id/<action>. */
export function useRequestAction() {
  return useLeaveMutation(({ id, action, body }: {
    id: number; action: string; body?: Record<string, unknown> }) =>
    http.post(`/leave/requests/${id}/${action}`, body ?? {}));
}

export function useReviewResumption() {
  return useLeaveMutation((id: number) => http.post(`/leave/resumptions/${id}/review`));
}

function useList<T>(path: string) {
  return useQuery({
    queryKey: [KEY, path],
    queryFn: async () => (await http.get<{ results: T[] }>(path)).data.results,
  });
}

export const usePolicies = () => useList<Policy>("/leave/settings/policies");
export const useUnits = () => useList<Unit>("/leave/settings/units");
export const useAuthorityRules = () => useList<AuthorityRule>("/leave/settings/authority-rules");
export const useCalendars = () => useList<HolidayCalendar>("/leave/calendars");

/** PUT or POST to an admin endpoint; the caller names both. */
export function useAdminWrite() {
  return useLeaveMutation(({ method, path, body }: {
    method: "post" | "put"; path: string; body?: unknown }) =>
    http[method](path, body ?? {}));
}
