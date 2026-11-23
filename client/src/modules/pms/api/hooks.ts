// One TanStack hook per PMS endpoint; every write refreshes the whole module's cache.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type {
  ApplicationDetail, ApplicationRow, AuditEntry, Budget, Candidate, Deadline, Escalation,
  LicensingRequest, MaintenanceCycle, OfficeAction, Oversight, Page, Person, PmsDocument,
  Policy, PriorArtReference, ReferenceData, Report, ReportDefinition, RosterEntry,
  SearchResult, WorkItem,
} from "./types";

const KEY = "pms";
type Body = Record<string, unknown>;

function useWrite<TArgs, TOut>(send: (args: TArgs) => Promise<TOut>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: send,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  return (await http.post<T>(`/pms/${path}`, body ?? {})).data;
}

async function get<T>(path: string, params?: Body): Promise<T> {
  return (await http.get<T>(`/pms/${path}`, { params })).data;
}

// -- reads ----------------------------------------------------------------------
export function useApplications(filters?: { status?: string; q?: string }) {
  return useQuery({ queryKey: [KEY, "applications", filters],
    queryFn: () => get<Page<ApplicationRow>>("applications", filters) });
}

export function useApplication(id: number | null) {
  return useQuery({ queryKey: [KEY, "application", id], enabled: id != null,
    queryFn: () => get<ApplicationDetail>(`applications/${id}`) });
}

export function useHistory(id: number | null) {
  return useQuery({ queryKey: [KEY, "history", id], enabled: id != null,
    queryFn: () => get<AuditEntry[]>(`applications/${id}/history`) });
}

export function useDocuments(id: number | null) {
  return useQuery({ queryKey: [KEY, "documents", id], enabled: id != null,
    queryFn: () => get<PmsDocument[]>(`applications/${id}/documents`) });
}

export function usePriorArt(id: number | null) {
  return useQuery({ queryKey: [KEY, "prior-art", id], enabled: id != null,
    queryFn: () => get<PriorArtReference[]>(`applications/${id}/prior-art`) });
}

export function useMyWork() {
  return useQuery({ queryKey: [KEY, "my-work"], queryFn: () => get<WorkItem[]>("my-work") });
}

export function useDirectorCandidates(id: number | null) {
  return useQuery({ queryKey: [KEY, "director-candidates", id], enabled: id != null,
    queryFn: () => get<Candidate[]>(`applications/${id}/director-candidates`) });
}

export function useAttorneyCandidates(id: number | null) {
  return useQuery({ queryKey: [KEY, "attorney-candidates", id], enabled: id != null,
    queryFn: () => get<Candidate[]>(`applications/${id}/attorney-candidates`) });
}

export function useDirectors() {
  return useQuery({ queryKey: [KEY, "directors"], queryFn: () => get<RosterEntry[]>("directors") });
}

export function usePanel() {
  return useQuery({ queryKey: [KEY, "panel"],
    queryFn: () => get<RosterEntry[]>("attorney-panel") });
}

export function usePanelOptions() {
  return useQuery({ queryKey: [KEY, "panel-options"],
    queryFn: () => get<{ user_id: number; name: string; domain_codes: string[] }[]>(
      "attorney-panel/options") });
}

export function useDeadlines() {
  return useQuery({ queryKey: [KEY, "deadlines"], queryFn: () => get<Deadline[]>("deadlines") });
}

export function useEscalations(status?: string) {
  return useQuery({ queryKey: [KEY, "escalations", status],
    queryFn: () => get<Escalation[]>("escalations", status ? { status } : undefined) });
}

export function useOversight() {
  return useQuery({ queryKey: [KEY, "oversight"], queryFn: () => get<Oversight>("oversight") });
}

export function useReport(type: string, filters?: Body) {
  return useQuery({ queryKey: [KEY, "report", type, filters],
    queryFn: () => get<Report>(`reports/${type}`, filters) });
}

export function useReportDefinitions(enabled: boolean) {
  return useQuery({ queryKey: [KEY, "report-definitions"], enabled,
    queryFn: () => get<ReportDefinition[]>("report-definitions") });
}

export function useAudit(filters?: Body) {
  return useQuery({ queryKey: [KEY, "audit", filters],
    queryFn: () => get<Page<AuditEntry>>("audit", filters) });
}

export function useLicensing() {
  return useQuery({ queryKey: [KEY, "licensing"],
    queryFn: () => get<LicensingRequest[]>("licensing-requests") });
}

export function useReferenceData() {
  return useQuery({ queryKey: [KEY, "reference-data"], staleTime: 60_000,
    queryFn: () => get<ReferenceData>("reference-data") });
}

export function usePolicy() {
  return useQuery({ queryKey: [KEY, "policy"], queryFn: () => get<Policy>("policy") });
}

export function useSetup() {
  return useQuery({ queryKey: [KEY, "setup"], queryFn: () => get<{ gaps: string[] }>("setup") });
}

export function usePeople(q: string, kind?: string) {
  return useQuery({ queryKey: [KEY, "people", q, kind], enabled: q.trim().length >= 2,
    queryFn: async () => (await get<{ results: Person[] }>("people", { q, kind })).results });
}

// -- applicant ---------------------------------------------------------------------
export const useCreateApplication = () =>
  useWrite((b: Body) => post<ApplicationDetail>("applications", b));
export const useUpdateApplication = () =>
  useWrite(async ({ id, ...b }: Body & { id: number }) =>
    (await http.patch<ApplicationDetail>(`/pms/applications/${id}`, b)).data);
export const useSubmit = () => useWrite((id: number) => post(`applications/${id}/submit`));
export const useReplaceInventors = () =>
  useWrite(async ({ id, inventors }: { id: number; inventors: Body[] }) =>
    (await http.put(`/pms/applications/${id}/inventors`, { inventors })).data);
export const useRecordAgreement = () =>
  useWrite(({ id, inventorId, ...b }: Body & { id: number; inventorId: number }) =>
    post(`applications/${id}/inventors/${inventorId}/agreement`, b));
export const useResubmit = () =>
  useWrite(({ id, responses }: { id: number; responses: Record<string, string> }) =>
    post(`applications/${id}/resubmit`, { responses }));
export const useWithdraw = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post(`applications/${id}/withdraw`, b));
export const useFileAppeal = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post(`applications/${id}/appeal`, b));
export const useApproveResponse = () =>
  useWrite((officeActionId: number) => post<OfficeAction>(`office-actions/${officeActionId}/approve`));

export function useUploadDocument() {
  return useWrite(async ({ id, file, ...fields }: { id: number; file: File } & Body) => {
    const form = new FormData();
    form.append("file", file);
    for (const [k, v] of Object.entries(fields)) {
      if (v !== undefined && v !== null && v !== "") form.append(k, String(v));
    }
    return (await http.post<PmsDocument[]>(`/pms/applications/${id}/documents`, form)).data;
  });
}

export function useDownloadVersion() {
  return useMutation({
    mutationFn: async ({ id, name }: { id: number; name: string }) => {
      try {
        const res = await http.get(`/pms/documents/versions/${id}/download`,
          { responseType: "blob" });
        saveBlob(res.data, filenameFromDisposition(res.headers["content-disposition"], name));
      } catch (e) {
        throw await readBlobError(e);
      }
    },
  });
}

export function useExport() {
  return useMutation({
    mutationFn: async ({ path, name }: { path: string; name: string }) => {
      try {
        const res = await http.get(`/pms/${path}`, { responseType: "blob" });
        saveBlob(res.data, filenameFromDisposition(res.headers["content-disposition"], name));
      } catch (e) {
        throw await readBlobError(e);
      }
    },
  });
}

// -- office -------------------------------------------------------------------------
export const useAssignDirector = () =>
  useWrite(({ id, director_user_id }: { id: number; director_user_id: number }) =>
    post(`applications/${id}/assign-director`, { director_user_id }));
export const useAssignAppeal = () =>
  useWrite(({ id, director_user_id }: { id: number; director_user_id: number }) =>
    post(`appeals/${id}/assign`, { director_user_id }));
export const useAssignAttorney = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post(`applications/${id}/assign-attorney`, b));
export const useSetDirector = () => useWrite((b: Body) => post<RosterEntry[]>("directors", b));
export const useEndDirector = () => useWrite((id: number) => post(`directors/${id}/end`));
export const useSetPanelAttorney = () =>
  useWrite((b: Body) => post<RosterEntry[]>("attorney-panel", b));
export const useEndPanelAttorney = () => useWrite((id: number) => post(`attorney-panel/${id}/end`));
export const useHandleEscalation = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post(`escalations/${id}/handle`, b));
export const useRouteBudget = () =>
  useWrite(({ id, routed_to }: { id: number; routed_to: string }) =>
    post<Budget>(`budgets/${id}/route`, { routed_to }));
export const useExternalDecision = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post<Budget>(`budgets/${id}/external-decision`, b));
export const useReassignRenewal = () =>
  useWrite(({ id, director_user_id }: { id: number; director_user_id: number }) =>
    post<MaintenanceCycle>(`maintenance-cycles/${id}/reassign`, { director_user_id }));
export const useSetSensitivity = () =>
  useWrite(async ({ id, sensitivity }: { id: number; sensitivity: string }) =>
    (await http.patch(`/pms/documents/${id}`, { sensitivity })).data);
export const usePublishPolicy = () =>
  useWrite((b: { based_on_version: number; payload: Body }) => post<Policy>("policy", b));
export const useRouteLicensing = () =>
  useWrite((id: number) => post<LicensingRequest>(`licensing-requests/${id}/route`));

// -- director -------------------------------------------------------------------------
export const useReviewDecision = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post(`applications/${id}/review`, b));
export const useAppealDecision = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post(`appeals/${id}/decision`, b));
export const useBudgetDecision = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post<Budget>(`budgets/${id}/decision`, b));
export const useRenewalDecision = () =>
  useWrite(({ id, ...b }: Body & { id: number }) =>
    post<MaintenanceCycle>(`maintenance-cycles/${id}/decision`, b));
export const useAddNote = () =>
  useWrite(({ id, note }: { id: number; note: string }) =>
    post<LicensingRequest>(`licensing-requests/${id}/notes`, { note }));
export const useRecordLicense = () =>
  useWrite(({ id, ...b }: Body & { id: number }) =>
    post<LicensingRequest>(`licensing-requests/${id}/agreement`, b));
export const useSubmitLicensing = () =>
  useWrite((b: Body) => post<LicensingRequest>("licensing-requests", b));

// -- attorney ---------------------------------------------------------------------------
export const useRespondAssignment = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post(`attorney-assignments/${id}/respond`, b));
export const useSaveAssessment = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post(`applications/${id}/assessments`, b));
export const useFinalizeAssessment = () =>
  useWrite((assessmentId: number) => post(`assessments/${assessmentId}/finalize`));
export const useLegalRequest = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post(`applications/${id}/legal-requests`, b));
export const useLegalAdvice = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post(`applications/${id}/legal-advice`, b));
export const useProposeBudget = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post<Budget>(`applications/${id}/budgets`, b));
export const useRecordFiling = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post(`applications/${id}/filings`, b));
export const useRecordCommunication = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post(`applications/${id}/communications`, b));
export const usePrepareResponse = () =>
  useWrite(({ id, draft }: { id: number; draft: string }) =>
    post<OfficeAction>(`office-actions/${id}/response`, { draft }));
export const useRecordSubmission = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post<OfficeAction>(`office-actions/${id}/submission`, b));
export const useRecordExtension = () =>
  useWrite(({ id, ...b }: Body & { id: number }) => post<OfficeAction>(`office-actions/${id}/extension`, b));
export const useAddCycle = () =>
  useWrite(({ id, due_on }: { id: number; due_on: string }) =>
    post<MaintenanceCycle>(`applications/${id}/maintenance-cycles`, { due_on }));
export const useRequestRenewal = () =>
  useWrite((cycleId: number) => post<MaintenanceCycle>(`maintenance-cycles/${cycleId}/request-decision`));
export const useRecordMaintenance = () =>
  useWrite(({ id, ...b }: Body & { id: number }) =>
    post<MaintenanceCycle>(`maintenance-cycles/${id}/action`, b));

// -- prior art and reports ----------------------------------------------------------------
export const useSearchPriorArt = () =>
  useMutation({ mutationFn: (b: Body) => post<SearchResult>("prior-art/searches", b) });
export const useAttachReference = () =>
  useWrite(({ id, ...b }: Body & { id: number }) =>
    post<PriorArtReference>(`applications/${id}/prior-art`, b));
export const useSaveReportDefinition = () =>
  useWrite((b: Body) => post<ReportDefinition>("report-definitions", b));
export const useDeactivateReport = () =>
  useWrite((id: number) => post<ReportDefinition>(`report-definitions/${id}/deactivate`));

// The IAM sends every held role's permissions; PMS screens use the acting role's only.
export function useActing() {
  return useQuery({ queryKey: [KEY, "acting"], staleTime: 30_000,
    queryFn: () => get<{ role: string; permissions: string[] }>("acting") });
}
