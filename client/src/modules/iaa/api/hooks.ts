import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type {
  Anomaly, BudgetEntry, Dashboard, FinancialRecord, FinancialYear, Observation, Page,
  PolicyVersion, RecordDetail, Summary, TrailEntry,
} from "./types";

const KEY = "iaa";

export const keys = {
  records: (f?: unknown) => [KEY, "records", f] as const,
  record: (id: number) => [KEY, "record", id] as const,
  history: (id: number) => [KEY, "history", id] as const,
  anomalies: (f?: unknown) => [KEY, "anomalies", f] as const,
  observations: (f?: unknown) => [KEY, "observations", f] as const,
  summary: () => [KEY, "summary"] as const,
  dashboard: () => [KEY, "dashboard"] as const,
  policies: () => [KEY, "policies"] as const,
  years: () => [KEY, "years"] as const,
  budget: () => [KEY, "budget"] as const,
};

// Every write can move several lists at once, so invalidate the whole module.
function useInvalidate() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

function useWrite<TVars, TResult>(fn: (v: TVars) => Promise<TResult>) {
  const invalidate = useInvalidate();
  return useMutation({ mutationFn: fn, onSuccess: () => invalidate() });
}

export type RecordFilters = { kind?: string; status?: string; queue?: string };

export function useRecords(filters?: RecordFilters) {
  return useQuery({
    queryKey: keys.records(filters),
    queryFn: async () =>
      (await http.get<Page<FinancialRecord>>("/iaa/records", { params: filters })).data,
  });
}

export function useRecord(id: number | null) {
  return useQuery({
    queryKey: keys.record(id ?? 0),
    enabled: id !== null,
    queryFn: async () => (await http.get<RecordDetail>(`/iaa/records/${id}`)).data,
  });
}

export function useHistory(id: number | null) {
  return useQuery({
    queryKey: keys.history(id ?? 0),
    enabled: id !== null,
    queryFn: async () => (await http.get<TrailEntry[]>(`/iaa/records/${id}/history`)).data,
  });
}

export const useCreateRecord = () =>
  useWrite((body: Record<string, unknown>) => http.post<FinancialRecord>("/iaa/records", body));
export const useUpdateDraft = () =>
  useWrite(({ id, ...body }: { id: number } & Record<string, unknown>) =>
    http.patch(`/iaa/records/${id}`, body));
export const useAddDocument = () =>
  useWrite(({ id, title, link }: { id: number; title: string; link: string }) =>
    http.post(`/iaa/records/${id}/documents`, { title, link }));
export const useSubmit = () => useWrite((id: number) => http.post(`/iaa/records/${id}/submit`));
export const useRaiseQuery = () =>
  useWrite(({ id, text }: { id: number; text: string }) =>
    http.post(`/iaa/records/${id}/query`, { text }));
export const useAnswerQuery = () =>
  useWrite(({ id, text }: { id: number; text: string }) =>
    http.post(`/iaa/records/${id}/query-response`, { text }));
export const useValidate = () =>
  useWrite(({ id, decision, remarks }: { id: number; decision: string; remarks: string }) =>
    http.post(`/iaa/records/${id}/validate`, { decision, remarks }));
export const useDecide = () =>
  useWrite(({ id, decision, remarks }: { id: number; decision: string; remarks: string }) =>
    http.post(`/iaa/records/${id}/decision`, { decision, remarks }));
export const useProcess = () =>
  useWrite(({ id, reference, note }: { id: number; reference: string; note: string }) =>
    http.post(`/iaa/records/${id}/processing`, { reference, note }));

export function useAnomalies(status?: string) {
  return useQuery({
    queryKey: keys.anomalies(status),
    queryFn: async () =>
      (await http.get<Page<Anomaly>>("/iaa/anomalies", { params: { status } })).data,
  });
}
export const useFlagAnomaly = () =>
  useWrite((body: { category: string; description: string; record_id?: number | null }) =>
    http.post("/iaa/anomalies", body));
export const useAnomalyAction = () =>
  useWrite(({ id, action, text }: { id: number; action: "resolve" | "escalate"; text: string }) =>
    http.post(`/iaa/anomalies/${id}/${action}`, { text }));

export function useObservations(status?: string) {
  return useQuery({
    queryKey: keys.observations(status),
    queryFn: async () =>
      (await http.get<Page<Observation>>("/iaa/observations", { params: { status } })).data,
  });
}
export const useRaiseObservation = () =>
  useWrite((body: { title: string; detail: string; record_id?: number | null;
                    respondent_user_id?: number | null }) =>
    http.post("/iaa/observations", body));
export const useRespondObservation = () =>
  useWrite(({ id, ...body }: { id: number; corrective_action: string; evidence_link: string }) =>
    http.post(`/iaa/observations/${id}/respond`, body));
export const useReviewObservation = () =>
  useWrite(({ id, ...body }: { id: number; verdict: string; remarks: string }) =>
    http.post(`/iaa/observations/${id}/review`, body));

export function useSummary() {
  return useQuery({
    queryKey: keys.summary(),
    queryFn: async () => (await http.get<Summary>("/iaa/reports/summary")).data,
  });
}

// Fetched rather than linked, so a refused or throttled export becomes a toast.
export function useExport() {
  return useMutation({
    mutationFn: async () => {
      try {
        const res = await http.get("/iaa/reports/export", { responseType: "blob" });
        saveBlob(res.data as Blob,
          filenameFromDisposition(res.headers["content-disposition"], "iaa-report.csv"));
      } catch (e) {
        throw await readBlobError(e);
      }
    },
  });
}

export function useDashboard() {
  return useQuery({
    queryKey: keys.dashboard(),
    queryFn: async () => (await http.get<Dashboard>("/iaa/notifications")).data,
  });
}

export function usePolicies() {
  return useQuery({
    queryKey: keys.policies(),
    queryFn: async () => (await http.get<PolicyVersion[]>("/iaa/config/policies")).data,
  });
}
export const usePublishPolicy = () =>
  useWrite((body: Record<string, unknown>) => http.post("/iaa/config/policies", body));

export function useYears() {
  return useQuery({
    queryKey: keys.years(),
    queryFn: async () => (await http.get<FinancialYear[]>("/iaa/config/financial-years")).data,
  });
}
export const useAddYear = () =>
  useWrite((body: { code: string; starts_on: string; ends_on: string }) =>
    http.post("/iaa/config/financial-years", body));

export function useBudget() {
  return useQuery({
    queryKey: keys.budget(),
    queryFn: async () =>
      (await http.get<Page<BudgetEntry>>("/iaa/config/budget-entries")).data,
  });
}
export const useAddBudgetEntry = () =>
  useWrite((body: { financial_year_id: number; department: string; kind: string;
                    amount: string; note: string }) =>
    http.post("/iaa/config/budget-entries", body));
