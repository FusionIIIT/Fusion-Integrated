import {
  useInfiniteQuery, useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  CursorPage, LeaveBalance, LeaveHoliday, LeaveLedgerEntry, LeavePolicy, LeaveRequest,
  LeaveTaskNotice,
} from "./types";

const KEY = "employee-leave";
const refresh = (client: ReturnType<typeof useQueryClient>) =>
  client.invalidateQueries({ queryKey: [KEY] });

export function useLeaveRequests() {
  return useQuery({
    queryKey: [KEY, "requests"],
    queryFn: async () => (await http.get<LeaveRequest[]>("/leave/requests")).data,
  });
}

export function useLeaveTasks() {
  return useQuery({
    queryKey: [KEY, "tasks"],
    queryFn: async () => (await http.get<LeaveRequest[]>("/leave/tasks")).data,
  });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: [KEY, "balances"],
    queryFn: async () =>
      (await http.get<{ balances: LeaveBalance[]; history: LeaveLedgerEntry[] }>(
        "/leave/balances")).data,
  });
}

export function useLeavePolicies() {
  return useInfiniteQuery({
    queryKey: [KEY, "policies"],
    initialPageParam: "/leave/policies",
    queryFn: async ({ pageParam }) =>
      (await http.get<CursorPage<LeavePolicy>>(pageParam)).data,
    getNextPageParam: (page) => page.next ?? undefined,
  });
}

export function useLeaveCalendar() {
  return useInfiniteQuery({
    queryKey: [KEY, "calendar"],
    initialPageParam: "/leave/calendar",
    queryFn: async ({ pageParam }) =>
      (await http.get<CursorPage<LeaveHoliday>>(pageParam)).data,
    getNextPageParam: (page) => page.next ?? undefined,
  });
}

export function useSubmitLeave() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<LeaveRequest>("/leave/requests", body)).data,
    onSuccess: () => refresh(client),
  });
}

export function useLeaveAction() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: { id: number; action: string; [key: string]: unknown }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/actions`, body)).data,
    onSuccess: () => refresh(client),
  });
}

export function useSubmitExtension() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: { id: number; [key: string]: unknown }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/extensions`, body)).data,
    onSuccess: () => refresh(client),
  });
}

export function useCreatePolicy() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<LeavePolicy>("/leave/policies", body)).data,
    onSuccess: () => refresh(client),
  });
}

export function useCreateHoliday() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<LeaveHoliday>("/leave/calendar", body)).data,
    onSuccess: () => refresh(client),
  });
}

export function usePublishHoliday() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveHoliday>(`/leave/calendar/${id}/publish`, {})).data,
    onSuccess: () => refresh(client),
  });
}

export function useAdjustBalance() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<LeaveLedgerEntry>("/leave/balances/adjust", body)).data,
    onSuccess: () => refresh(client),
  });
}

export function useRecordOfflineLeave() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<LeaveRequest>("/leave/requests/offline", body)).data,
    onSuccess: () => refresh(client),
  });
}

export function useProcessYearEnd() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (from_year: number) =>
      (await http.post<{
        id: number; from_year: number; to_year: number; balances_processed: number;
        annual_credits: string; carried_forward: string; converted_to_el: string;
        lapsed: string; created_at: string;
      }>("/leave/year-end", { from_year })).data,
    onSuccess: () => refresh(client),
  });
}

export function usePrintLeaveRequest() {
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.get<string>(`/leave/requests/${id}/print`, { responseType: "text" })).data,
  });
}

export function useTaskNotices() {
  return useQuery({
    queryKey: [KEY, "notices"],
    queryFn: async () =>
      (await http.get<LeaveTaskNotice[]>("/leave/notices")).data,
  });
}

export function useAcknowledgeTaskNotice() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveTaskNotice>(`/leave/notices/${id}/read`, {})).data,
    onSuccess: () => refresh(client),
  });
}