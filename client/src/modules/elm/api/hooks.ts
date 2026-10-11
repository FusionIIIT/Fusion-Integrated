/** Data access for the ELM module.
 *
 *  Every mutation invalidates the keys it can affect; pages never hand-edit
 *  the cache. */
import {
  useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  ApplicationPayload, Balance, ElmContext, HolidayCalendar,
  LeaveRecordItem, LeaveRequest, Page, TaskWithRequest,
} from "./types";

const KEY = "elm";

export const keys = {
  context: () => [KEY, "context"] as const,
  balances: (leaveYear?: string) => [KEY, "balances", leaveYear] as const,
  requests: (f?: unknown) => [KEY, "requests", f] as const,
  request: (id: number) => [KEY, "request", id] as const,
  queue: () => [KEY, "queue"] as const,
  substituteTasks: () => [KEY, "substitute-tasks"] as const,
  records: (f?: unknown) => [KEY, "records", f] as const,
  calendar: () => [KEY, "calendar"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- context -------------------------------------------------------------------
export function useElmContext() {
  return useQuery({
    queryKey: keys.context(),
    queryFn: async () => (await http.get<ElmContext>("/elm/me")).data,
    staleTime: 60_000,
  });
}

// -- balances ------------------------------------------------------------------
export function useBalances(leaveYear?: string) {
  return useQuery({
    queryKey: keys.balances(leaveYear),
    queryFn: async () =>
      (await http.get<Balance[]>("/elm/balances", {
        params: leaveYear ? { leave_year: leaveYear } : {},
      })).data,
    staleTime: 30_000,
  });
}

// -- applications ----------------------------------------------------------------
export function useRequests(filters?: { category?: string; status?: string }) {
  return useQuery({
    queryKey: keys.requests(filters),
    queryFn: async () =>
      (await http.get<Page<LeaveRequest>>("/elm/requests", { params: filters }))
        .data,
    staleTime: 15_000,
  });
}

export function useRequest(id: number | undefined) {
  return useQuery({
    queryKey: keys.request(id!),
    queryFn: async () =>
      (await http.get<LeaveRequest>(`/elm/requests/${id}`)).data,
    enabled: id != null,
  });
}

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ApplicationPayload) =>
      (await http.post<LeaveRequest>("/elm/requests", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdraw() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason?: string }) =>
      (await http.post<LeaveRequest>(`/elm/requests/${id}/withdraw`, { reason }))
        .data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useNominateSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (
      { id, nominee_user_id }: { id: number; nominee_user_id: number },
    ) =>
      (await http.post<LeaveRequest>(`/elm/requests/${id}/substitute`, {
        nominee_user_id,
      })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- queue and decisions ---------------------------------------------------------
export function useQueue() {
  return useQuery({
    queryKey: keys.queue(),
    queryFn: async () =>
      (await http.get<TaskWithRequest[]>("/elm/queue")).data,
    staleTime: 10_000,
  });
}

export function useSubstituteTasks() {
  return useQuery({
    queryKey: keys.substituteTasks(),
    queryFn: async () =>
      (await http.get<TaskWithRequest[]>("/elm/substitute-tasks")).data,
    staleTime: 10_000,
  });
}

export function useDecide() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (
      { taskId, outcome, reason }:
        { taskId: number; outcome: string; reason?: string },
    ) =>
      (await http.post<LeaveRequest>(`/elm/tasks/${taskId}/decide`, {
        outcome, reason,
      })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRespondSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (
      { taskId, accept, reason }:
        { taskId: number; accept: boolean; reason?: string },
    ) =>
      (await http.post<LeaveRequest>(
        `/elm/substitute-tasks/${taskId}/respond`, { accept, reason })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- lifecycle -----------------------------------------------------------------
export function useRequestCancellation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      base_request_id: number; effective_date?: string; reason?: string;
    }) =>
      (await http.post<LeaveRequest>("/elm/cancellations", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRequestExtension() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      base_request_id: number; start_date: string; end_date: string;
      purpose: string; substitute_required?: boolean;
      substitute_user_id?: number | null; reason?: string;
    }) =>
      (await http.post<LeaveRequest>("/elm/extensions", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      record_id: number; actual_resumption_date: string; details?: string;
    }) => (await http.post("/elm/resumptions", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- records --------------------------------------------------------------------
export function useRecords(filters?: { unit?: string; category?: string }) {
  return useQuery({
    queryKey: keys.records(filters),
    queryFn: async () =>
      (await http.get<LeaveRecordItem[]>("/elm/records", { params: filters }))
        .data,
    staleTime: 30_000,
  });
}

export function useRecordOffline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await http.post("/elm/records/offline", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- calendar --------------------------------------------------------------------
export function useCalendar() {
  return useQuery({
    queryKey: keys.calendar(),
    queryFn: async () =>
      (await http.get<HolidayCalendar | { published: false }>("/elm/calendar"))
        .data,
    staleTime: 60_000,
  });
}
