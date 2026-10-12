import {
  useMutation, useQuery, useQueryClient, type UseMutationOptions,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import { filenameFromDisposition, saveBlob } from "../../../lib/http";
import type {
  HolidayCalendar, LeaveAccount, LeaveRequest,
  LeaveTypeConfig, Page, SlaConfig, SubstituteAssignment, VacationPeriod,
  WorkflowTask,
} from "./types";

const KEY = "elm";

export const keys = {
  requests: (f?: unknown) => [KEY, "requests", f] as const,
  request: (id: number) => [KEY, "request", id] as const,
  tasks: () => [KEY, "tasks"] as const,
  substitutions: () => [KEY, "substitutions"] as const,
  accounts: (year?: number) => [KEY, "accounts", year] as const,
  ledger: (f?: unknown) => [KEY, "ledger", f] as const,
  policy: () => [KEY, "policy"] as const,
  calendars: () => [KEY, "calendars"] as const,
  vacations: () => [KEY, "vacations"] as const,
  records: () => [KEY, "records"] as const,
  sla: () => [KEY, "sla"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Requests ------------------------------------------------------------------
export function useMyRequests(filters?: Record<string, unknown>) {
  return useQuery({
    queryKey: keys.requests(filters),
    queryFn: async () =>
      (await http.get<Page<LeaveRequest>>("/elm/requests", { params: filters })).data,
    staleTime: 30_000,
  });
}

export function useCreateRequest(opt?: UseMutationOptions<LeaveRequest, unknown, any, unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: any) => (await http.post<LeaveRequest>("/elm/requests", payload)).data,
    onSuccess: (data: LeaveRequest, variables: any, context: unknown, _a: any) => {
      invalidateAll(qc);
      if (opt?.onSuccess) (opt.onSuccess as any)(data, variables, context, _a);
    },
    onError: opt?.onError,
  });
}

export function useWithdraw(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload?: any) => (await http.post<LeaveRequest>(`/elm/requests/${id}/withdraw`, payload ?? {})).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCancel(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await http.post<LeaveRequest>(`/elm/requests/${id}/cancel`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useExtend(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: any) => (await http.post<LeaveRequest>(`/elm/requests/${id}/extend`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useTaskQueue() {
  return useQuery({
    queryKey: keys.tasks(),
    queryFn: async () => (await http.get<WorkflowTask[]>("/elm/tasks")).data,
  });
}

export function useSubstitutions() {
  return useQuery({
    queryKey: keys.substitutions(),
    queryFn: async () => (await http.get<SubstituteAssignment[]>("/elm/substitutions")).data,
  });
}

export function useRespondToSubstitution(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: any) => (await http.post<SubstituteAssignment>(`/elm/substitutions/${id}/respond`, payload)).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: keys.substitutions() }); qc.invalidateQueries({ queryKey: keys.tasks() }); },
  });
}

export function useReviewUnitHead(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: any) => (await http.post<LeaveRequest>(`/elm/requests/${id}/review`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useEstablishment(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload?: any) => (await http.post<LeaveRequest>(`/elm/requests/${id}/establishment`, payload ?? {})).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSanction(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: any) => (await http.post<LeaveRequest>(`/elm/requests/${id}/sanction`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useExportRequests() {
  return useMutation({
    mutationFn: async () => {
      const r = await http.get("/elm/requests/export.csv", { responseType: "blob" });
      const fn = filenameFromDisposition((r.headers as any)?.["content-disposition"]) ?? "leave.csv";
      saveBlob(r.data as Blob, fn);
    },
  });
}

export function useAccounts(year?: number) {
  return useQuery({
    queryKey: keys.accounts(year),
    queryFn: async () => (await http.get<LeaveAccount[]>("/elm/accounts", { params: { year } })).data,
  });
}

export function usePolicy() {
  return useQuery({
    queryKey: keys.policy(),
    queryFn: async () => (await http.get<{ leave_types: LeaveTypeConfig[] }>("/elm/policy")).data,
  });
}

export function useCalendars() {
  return useQuery({
    queryKey: keys.calendars(),
    queryFn: async () => (await http.get<HolidayCalendar[]>("/elm/calendars")).data,
  });
}

export function useVacations() {
  return useQuery({
    queryKey: keys.vacations(),
    queryFn: async () => (await http.get<VacationPeriod[]>("/elm/vacations")).data,
  });
}

export function useRecords() {
  return useQuery({
    queryKey: keys.records(),
    queryFn: async () => (await http.get<LeaveRequest[]>("/elm/records")).data,
  });
}

export function useSla() {
  return useQuery({
    queryKey: keys.sla(),
    queryFn: async () => (await http.get<SlaConfig[]>("/elm/sla")).data,
  });
}
