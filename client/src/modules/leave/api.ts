import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../lib/http";

type Page<T> = { results: T[] };
export type LeaveCategory = { code: string; label: string; description: string };
export type LeaveRequest = {
  id: number; category_code: string; request_type: string; status: string;
  start_date: string; end_date: string; duration_days: string; reason: string;
};
export type LeaveBalance = {
  id: number; category_code: string; year: number; entitlement: string;
  carried_over: string; available: string;
};

const key = ["leave"] as const;
export function useMyLeave() {
  const categories = useQuery({ queryKey: [...key, "categories"], queryFn: async () =>
    (await http.get<Page<LeaveCategory>>("/leave/categories")).data });
  const requests = useQuery({ queryKey: [...key, "requests"], queryFn: async () =>
    (await http.get<Page<LeaveRequest>>("/leave/requests")).data });
  const balances = useQuery({ queryKey: [...key, "balances"], queryFn: async () =>
    (await http.get<Page<LeaveBalance>>("/leave/balances")).data });
  return { categories, requests, balances };
}

export function useEmployeeSearch(query: string) {
  return useQuery({ queryKey: [...key, "employees", query], queryFn: async () =>
    (await http.get<{ user_id: number; label: string; kind: string }[]>("/leave/employees", { params: { q: query } })).data,
    enabled: query.trim().length >= 2,
    staleTime: 30_000,
  });
}

export function useApplyForLeave() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const draft = (await http.post<LeaveRequest>("/leave/requests", body)).data;
      return (await http.post<LeaveRequest>(`/leave/requests/${draft.id}/submit`, {})).data;
    },
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
}

export function useWithdrawLeave() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/withdraw`, {})).data,
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
}

export type LeaveTask = { id: number; request_id: number; employee_id: number; category_code: string; sequence: number; role: string; state: string };
export function useTasks() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: [...key, "tasks"], queryFn: async () =>
    (await http.get<Page<LeaveTask>>("/leave/tasks")).data });
  const decide = useMutation({
    mutationFn: async ({ id, decision }: { id: number; decision: string }) =>
      (await http.post(`/leave/tasks/${id}/decision`, { decision })).data,
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
  return { ...query, decide };
}

export function useSubstitutions() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: [...key, "substitutions"], queryFn: async () =>
    (await http.get<Page<LeaveRequest>>("/leave/substitutions")).data });
  const respond = useMutation({
    mutationFn: async ({ id, decision }: { id: number; decision: "accept" | "decline" }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/substitute-response`, { decision })).data,
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
  return { ...query, respond };
}

export type LeaveCalendar = { id: number; year: number; revision: number; holidays: { date: string; description?: string; type?: string; restricted_holiday?: boolean }[] };
export function useLeaveCalendars() {
  return useQuery({ queryKey: [...key, "calendars"], queryFn: async () =>
    (await http.get<Page<LeaveCalendar>>("/leave/calendars")).data });
}
