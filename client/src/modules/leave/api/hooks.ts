import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  AuthorityRoute, BalancesResponse, LeaveApplication, LeaveCalendar, LeavePolicy,
  LeaveType, Resumption, SlaConfiguration,
} from "./types";

const KEY = "leave";
const api = "/leave";
const invalidate = (client: ReturnType<typeof useQueryClient>) =>
  client.invalidateQueries({ queryKey: [KEY] });

export function useApplications() {
  return useQuery({
    queryKey: [KEY, "applications"],
    queryFn: async () => (await http.get<LeaveApplication[]>(`${api}/applications`)).data,
  });
}

export function useAssignedTasks() {
  return useQuery({
    queryKey: [KEY, "tasks"],
    queryFn: async () => (await http.get<LeaveApplication[]>(`${api}/tasks`)).data,
  });
}

export function useBalances() {
  return useQuery({
    queryKey: [KEY, "balances"],
    queryFn: async () => (await http.get<BalancesResponse>(`${api}/balances`)).data,
  });
}

export function useResumptions() {
  return useQuery({
    queryKey: [KEY, "resumptions"],
    queryFn: async () => (await http.get<Resumption[]>(`${api}/resumptions`)).data,
  });
}

export function useLeaveAdmin() {
  const policies = useQuery({
    queryKey: [KEY, "policies"],
    queryFn: async () => (await http.get<LeavePolicy[]>(`${api}/admin/policies`)).data,
  });
  const routes = useQuery({
    queryKey: [KEY, "routes"],
    queryFn: async () => (await http.get<AuthorityRoute[]>(`${api}/admin/routes`)).data,
  });
  const calendars = useQuery({
    queryKey: [KEY, "calendars"],
    queryFn: async () => (await http.get<LeaveCalendar[]>(`${api}/admin/calendars`)).data,
  });
  const sla = useQuery({
    queryKey: [KEY, "sla"],
    queryFn: async () => (await http.get<SlaConfiguration[]>(`${api}/admin/sla`)).data,
  });
  return { policies, routes, calendars, sla };
}

export function useCreateApplication() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (data: Record<string, unknown>) =>
      (await http.post<LeaveApplication>(`${api}/applications`, data)).data,
    onSuccess: () => invalidate(client),
  });
}

export function useAction() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...data }: { id: number; event: string; outcome?: string;
      note?: string; substitute_user_id?: number }) =>
      (await http.post<LeaveApplication>(`${api}/applications/${id}/action`, data)).data,
    onSuccess: () => invalidate(client),
  });
}

export function useCancellation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (original_application_id: number) =>
      (await http.post<LeaveApplication>(`${api}/cancellations`, {
        original_application_id,
      })).data,
    onSuccess: () => invalidate(client),
  });
}

export function useExtension() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (data: { original_application_id: number; end_date: string;
      purpose?: string; substitute_user_id?: number }) =>
      (await http.post<LeaveApplication>(`${api}/extensions`, data)).data,
    onSuccess: () => invalidate(client),
  });
}

export function useCreateResumption() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (data: { application_id: number; actual_resumption_date: string }) =>
      (await http.post<Resumption>(`${api}/resumptions`, data)).data,
    onSuccess: () => invalidate(client),
  });
}

export function useReviewResumption() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<Resumption>(`${api}/resumptions/${id}/review`)).data,
    onSuccess: () => invalidate(client),
  });
}

export function useSavePolicy() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (data: Record<string, unknown>) =>
      (await http.post<LeavePolicy>(`${api}/admin/policies`, data)).data,
    onSuccess: () => invalidate(client),
  });
}

export function useSaveRoute() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (data: Record<string, unknown>) =>
      (await http.post<AuthorityRoute>(`${api}/admin/routes`, data)).data,
    onSuccess: () => invalidate(client),
  });
}

export function useCreateCalendar() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (data: Record<string, unknown>) =>
      (await http.post<LeaveCalendar>(`${api}/admin/calendars`, data)).data,
    onSuccess: () => invalidate(client),
  });
}

export function usePublishCalendar() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveCalendar>(`${api}/admin/calendars/${id}/publish`)).data,
    onSuccess: () => invalidate(client),
  });
}

export function useSaveSla() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (data: Record<string, unknown>) =>
      (await http.post<SlaConfiguration>(`${api}/admin/sla`, data)).data,
    onSuccess: () => invalidate(client),
  });
}

export function useOfflineLeave() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (data: Record<string, unknown>) =>
      (await http.post<LeaveApplication>(`${api}/admin/offline-leave`, data)).data,
    onSuccess: () => invalidate(client),
  });
}

export function useRecordCorrection() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (data: Record<string, unknown>) =>
      (await http.post(`${api}/admin/record-corrections`, data)).data,
    onSuccess: () => invalidate(client),
  });
}

export function leaveTypes(): LeaveType[] {
  return ["CL", "RH", "SCL", "EL", "COL", "VL"];
}
