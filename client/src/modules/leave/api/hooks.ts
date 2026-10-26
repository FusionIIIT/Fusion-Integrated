/** Data access for Leave; every mutation invalidates the whole module, correctness over a refetch. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type {
  Action, ApplyInput, EffectiveCalendar, EmployeeRecord, Hierarchy, HolidayCalendar, Holiday,
  LeaveRequest, LeaveRequestDetail, LedgerEntry, Overview, Page, Person, Policy, QueueTask,
  Readiness, Resumption, SlaRule, SubstitutionRequest, Vacation, YearEndRun, OrgUnit,
  SanctionRoute, CategoryRule,
} from "./types";

const KEY = "leave";

export const keys = {
  overview: (year?: number) => [KEY, "overview", year] as const,
  ledger: (year?: number) => [KEY, "ledger", year] as const,
  requests: () => [KEY, "requests"] as const,
  request: (id: number) => [KEY, "request", id] as const,
  calendar: (year: number) => [KEY, "calendar", year] as const,
  employees: (q: string) => [KEY, "employees", q] as const,
  substitutions: () => [KEY, "substitutions"] as const,
  queue: () => [KEY, "queue"] as const,
  policy: () => [KEY, "policy"] as const,
  hierarchy: () => [KEY, "hierarchy"] as const,
  sla: () => [KEY, "sla"] as const,
  calendars: (year: number) => [KEY, "calendars", year] as const,
  vacations: () => [KEY, "vacations"] as const,
  record: (userId: number, year: number) => [KEY, "record", userId, year] as const,
  yearEnd: () => [KEY, "year-end"] as const,
  readiness: () => [KEY, "readiness"] as const,
};

function useLeaveMutation<TVars, TOut>(fn: (v: TVars) => Promise<TOut>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}

// -- employee ------------------------------------------------------------------
export function useOverview(year?: number) {
  return useQuery({
    queryKey: keys.overview(year),
    queryFn: async () => (await http.get<Overview>("/leave/overview",
      { params: year ? { year } : undefined })).data,
  });
}

export function useLedger(year?: number) {
  return useQuery({
    queryKey: keys.ledger(year),
    queryFn: async () => (await http.get<Page<LedgerEntry>>("/leave/ledger",
      { params: { year, limit: 100 } })).data,
  });
}

export function useMyRequests() {
  return useQuery({
    queryKey: keys.requests(),
    queryFn: async () => (await http.get<LeaveRequest[]>("/leave/requests")).data,
  });
}

export function useRequest(id: number | null) {
  return useQuery({
    queryKey: keys.request(id ?? 0),
    queryFn: async () => (await http.get<LeaveRequestDetail>(`/leave/requests/${id}`)).data,
    enabled: id != null,
  });
}

export function useEffectiveCalendar(year: number) {
  return useQuery({
    queryKey: keys.calendar(year),
    queryFn: async () => (await http.get<EffectiveCalendar>("/leave/calendar",
      { params: { year } })).data,
    staleTime: 5 * 60_000,
  });
}

export function useEmployeeSearch(q: string) {
  return useQuery({
    queryKey: keys.employees(q),
    queryFn: async () => (await http.get<Person[]>("/leave/employees", { params: { q } })).data,
    enabled: q.trim().length >= 2,
    staleTime: 60_000,
  });
}

export function useApply() {
  return useLeaveMutation(async (body: ApplyInput) =>
    (await http.post<LeaveRequestDetail>("/leave/requests", body)).data);
}

export function useWithdraw() {
  return useLeaveMutation(async ({ id, reason }: { id: number; reason: string }) =>
    (await http.post<LeaveRequestDetail>(`/leave/requests/${id}/withdraw`, { reason })).data);
}

export function useRequestCancellation() {
  return useLeaveMutation(async ({ id, reason }: { id: number; reason: string }) =>
    (await http.post<LeaveRequestDetail>(`/leave/requests/${id}/cancellation`, { reason })).data);
}

export function useRequestExtension() {
  return useLeaveMutation(async ({ id, ...body }: { id: number } & Omit<ApplyInput,
    "category" | "start_date">) =>
    (await http.post<LeaveRequestDetail>(`/leave/requests/${id}/extension`, body)).data);
}

export function useRenominate() {
  return useLeaveMutation(async ({ id, substitute_user_id }: {
    id: number; substitute_user_id: number;
  }) => (await http.post<LeaveRequestDetail>(`/leave/requests/${id}/substitute`,
    { substitute_user_id })).data);
}

export function useSubmitResumption() {
  return useLeaveMutation(async ({ id, ...body }: {
    id: number; resumption_date: string; details: string;
  }) => (await http.post<Resumption>(`/leave/requests/${id}/resumption`, body)).data);
}

/** EL-UC-013: fetched, not navigated to, so a refusal is a toast rather than a lost page. */
export function useDownloadApplication() {
  return useMutation({
    mutationFn: async (id: number) => {
      try {
        const r = await http.get<Blob>(`/leave/requests/${id}/document`,
          { responseType: "blob" });
        saveBlob(r.data, filenameFromDisposition(r.headers["content-disposition"],
          `leave-${id}.html`));
      } catch (e) {
        throw await readBlobError(e);
      }
    },
  });
}

// -- substitute and approvers -------------------------------------------------------
export function useSubstitutions() {
  return useQuery({
    queryKey: keys.substitutions(),
    queryFn: async () => (await http.get<SubstitutionRequest[]>("/leave/substitutions")).data,
  });
}

export function useRespond() {
  return useLeaveMutation(async ({ id, accept, remarks }: {
    id: number; accept: boolean; remarks: string;
  }) => (await http.post<LeaveRequest>(`/leave/substitutions/${id}/respond`,
    { accept, remarks })).data);
}

export function useQueue() {
  return useQuery({
    queryKey: keys.queue(),
    queryFn: async () => (await http.get<QueueTask[]>("/leave/queue")).data,
  });
}

export function useDecide() {
  return useLeaveMutation(async ({ id, action, remarks }: {
    id: number; action: Action; remarks: string;
  }) => (await http.post<LeaveRequestDetail>(`/leave/tasks/${id}/decide`,
    { action, remarks })).data);
}

// -- administration -----------------------------------------------------------------
export function usePolicy() {
  return useQuery({ queryKey: keys.policy(),
    queryFn: async () => (await http.get<Policy>("/leave/admin/policy")).data });
}

export function useSavePolicy() {
  return useLeaveMutation(async (body: { rules: CategoryRule[]; weekend_days: number[];
    max_backdate_days: number; note: string; }) =>
    (await http.post<Policy>("/leave/admin/policy", body)).data);
}

export function useHierarchy() {
  return useQuery({ queryKey: keys.hierarchy(),
    queryFn: async () => (await http.get<Hierarchy>("/leave/admin/hierarchy")).data });
}

export function useSaveHierarchy() {
  return useLeaveMutation(async (body: { units: OrgUnit[]; routes: SanctionRoute[];
    note: string; }) => (await http.post<Hierarchy>("/leave/admin/hierarchy", body)).data);
}

export function useSla() {
  return useQuery({ queryKey: keys.sla(),
    queryFn: async () => (await http.get<{ rules: SlaRule[] }>("/leave/admin/sla")).data });
}

export function useSaveSla() {
  return useLeaveMutation(async (body: { rules: SlaRule[]; note: string }) =>
    (await http.post<{ rules: SlaRule[] }>("/leave/admin/sla", body)).data);
}

export function useCalendars(year: number) {
  return useQuery({ queryKey: keys.calendars(year),
    queryFn: async () => (await http.get<HolidayCalendar[]>("/leave/admin/calendars",
      { params: { year } })).data });
}

export function useStartCalendar() {
  return useLeaveMutation(async (year: number) =>
    (await http.post<HolidayCalendar>("/leave/admin/calendars", { year })).data);
}

export function useSaveCalendar() {
  return useLeaveMutation(async ({ id, holidays }: { id: number; holidays: Holiday[] }) =>
    (await http.put<HolidayCalendar>(`/leave/admin/calendars/${id}`, { holidays })).data);
}

export function usePublishCalendar() {
  return useLeaveMutation(async (id: number) =>
    (await http.post<HolidayCalendar>(`/leave/admin/calendars/${id}/publish`)).data);
}

export function useVacations() {
  return useQuery({ queryKey: keys.vacations(),
    queryFn: async () => (await http.get<Vacation[]>("/leave/admin/vacations")).data });
}

export function useAddVacation() {
  return useLeaveMutation(async (body: Omit<Vacation, "id">) =>
    (await http.post<Vacation>("/leave/admin/vacations", body)).data);
}

export function useRemoveVacation() {
  return useLeaveMutation(async (id: number) => {
    await http.delete(`/leave/admin/vacations/${id}`);
  });
}

export function useEmployeeRecord(userId: number | null, year: number) {
  return useQuery({
    queryKey: keys.record(userId ?? 0, year),
    queryFn: async () => (await http.get<EmployeeRecord>("/leave/admin/records",
      { params: { user_id: userId, year } })).data,
    enabled: userId != null,
  });
}

export function useRecordOffline() {
  return useLeaveMutation(async (body: Record<string, unknown>) =>
    (await http.post<LeaveRequest>("/leave/admin/records/offline", body)).data);
}

export function useAdjust() {
  return useLeaveMutation(async (body: Record<string, unknown>) =>
    (await http.post<LedgerEntry>("/leave/admin/records/adjustments", body)).data);
}

export function useYearEnd() {
  return useQuery({ queryKey: keys.yearEnd(),
    queryFn: async () => (await http.get<YearEndRun[]>("/leave/admin/year-end")).data });
}

export function useReadiness() {
  return useQuery({ queryKey: keys.readiness(),
    queryFn: async () => (await http.get<Readiness>("/leave/admin/readiness")).data });
}
