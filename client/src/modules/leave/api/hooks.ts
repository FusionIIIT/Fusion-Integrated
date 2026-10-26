import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  ApplyPayload, BalanceResponse, LeaveCalendar, LeavePolicy, LeaveRequest,
  LeaveTask, Page,
} from "./types";

const KEY = "leave";

export const keys = {
  requests: (kind?: string) => [KEY, "requests", kind] as const,
  balances: (year?: string) => [KEY, "balances", year] as const,
  substitutions: () => [KEY, "substitutions"] as const,
  inbox: () => [KEY, "inbox"] as const,
  all: (filters?: { status?: string; category?: string; kind?: string }) => [KEY, "all", filters] as const,
  policy: () => [KEY, "policy"] as const,
  calendars: (year?: string) => [KEY, "calendars", year] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

export function useMyRequests(kind?: string) {
  return useQuery({
    queryKey: keys.requests(kind),
    queryFn: async () =>
      (await http.get<Page<LeaveRequest>>(`/leave/requests`, { params: kind ? { kind } : undefined })).data,
    staleTime: 15_000,
  });
}

export function useBalances(year?: string) {
  return useQuery({
    queryKey: keys.balances(year),
    queryFn: async () =>
      (await http.get<BalanceResponse>(`/leave/balances`, { params: year ? { year } : undefined })).data,
  });
}

export function useSubstitutions() {
  return useQuery({
    queryKey: keys.substitutions(),
    queryFn: async () =>
      (await http.get<Page<LeaveRequest>>(`/leave/substitutions`)).data,
  });
}

export function useInbox() {
  return useQuery({
    queryKey: keys.inbox(),
    queryFn: async () =>
      (await http.get<Page<LeaveTask>>(`/leave/inbox`)).data,
    staleTime: 15_000,
  });
}

export function useAllRequests(filters?: { status?: string; category?: string; kind?: string }) {
  return useQuery({
    queryKey: keys.all(filters),
    queryFn: async () =>
      (await http.get<Page<LeaveRequest>>(`/leave/all`, { params: filters })).data,
  });
}

export function usePolicy() {
  return useQuery({
    queryKey: keys.policy(),
    queryFn: async () =>
      (await http.get<LeavePolicy>(`/leave/policy`)).data,
    retry: false,
  });
}

export function useCalendars(year?: string) {
  return useQuery({
    queryKey: keys.calendars(year),
    queryFn: async () =>
      (await http.get<Page<LeaveCalendar>>(`/leave/calendars`, { params: year ? { year } : undefined })).data,
  });
}

export function useApply() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ApplyPayload) =>
      (await http.post<LeaveRequest>(`/leave/requests`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdraw() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason: string }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/withdraw`, { reason })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRespond() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, accept }: { id: number; accept: boolean }) =>
      (await http.post<LeaveRequest>(`/leave/substitutions/${id}`, { accept })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSavePolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<LeavePolicy>) =>
      (await http.post<LeavePolicy>(`/leave/policy`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublishCalendar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveCalendar>(`/leave/calendars/${id}/publish`, {})).data,
    onSuccess: () => invalidateAll(qc),
  });
}
