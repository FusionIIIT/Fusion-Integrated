import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type { Balances, LeaveApplication, LeavePolicy, Page, WorkflowTask } from "./types";

const KEY = "leave";

function invalidate(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

export function useApplications() {
  return useQuery({
    queryKey: [KEY, "applications"],
    queryFn: async () =>
      (await http.get<Page<LeaveApplication>>("/leave/applications")).data,
  });
}

export function useBalances() {
  return useQuery({
    queryKey: [KEY, "balances"],
    queryFn: async () => (await http.get<Balances>("/leave/balances")).data,
  });
}

export function useTasks() {
  return useQuery({
    queryKey: [KEY, "tasks"],
    queryFn: async () => (await http.get<Page<WorkflowTask>>("/leave/tasks")).data,
  });
}

export function usePolicy() {
  return useQuery({
    queryKey: [KEY, "policy"],
    queryFn: async () => (await http.get<LeavePolicy>("/leave/policy")).data,
  });
}

export function useCalendar() {
  return useQuery({
    queryKey: [KEY, "calendar"],
    queryFn: async () => (await http.get("/leave/calendar")).data,
  });
}

export function useSubmitLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<LeaveApplication>("/leave/applications", body)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useLeaveAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, path, body }: {
      id: number; path: string; body?: Record<string, unknown>;
    }) =>
      (await http.post<LeaveApplication>(`/leave/applications/${id}/${path}`, body ?? {})).data,
    onSuccess: () => invalidate(qc),
  });
}

export function usePublishPolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<LeavePolicy>("/leave/policy", body)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function usePublishCalendar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post("/leave/calendar", body)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useRecordOffline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<LeaveApplication>("/leave/offline", body)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function downloadApplication(id: number) {
  return http.get(`/leave/applications/${id}/export`, { responseType: "blob" });
}
