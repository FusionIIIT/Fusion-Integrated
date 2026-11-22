/** Data access hooks for the patents module using TanStack Query.
 *
 * Every mutation invalidates the queries it can affect; no manual cache surgery.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  AppealRecord,
  AttorneyPanelMember,
  AuditLogsResponse,
  CreateApplicationInput,
  Page,
  PatentApplicationDetail,
  PatentApplicationSummary,
  PriorArtResult,
  ReportsResponse,
  ReviewDecision,
} from "./types";

const KEY = "patents";

export const keys = {
  all: () => [KEY] as const,
  applications: (filters?: unknown) => [KEY, "applications", filters] as const,
  application: (id?: number) => [KEY, "application", id] as const,
  attorneyPanel: () => [KEY, "attorney-panel"] as const,
  reports: () => [KEY, "reports"] as const,
  auditLogs: () => [KEY, "audit-logs"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Applications Queries ------------------------------------------------------

export function useApplications(filters?: Record<string, string | number>) {
  return useQuery({
    queryKey: keys.applications(filters),
    queryFn: async () =>
      (await http.get<Page<PatentApplicationSummary>>("/patents/applications", { params: filters })).data,
    staleTime: 30_000,
  });
}

export function useApplication(id: number | undefined) {
  return useQuery({
    queryKey: keys.application(id),
    queryFn: async () => {
      if (!id) throw new Error("Application ID is required");
      return (await http.get<PatentApplicationDetail>(`/patents/applications/${id}`)).data;
    },
    enabled: typeof id === "number" && id > 0,
    staleTime: 30_000,
  });
}

// -- Application Lifecycle Mutations -------------------------------------------

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateApplicationInput) =>
      (await http.post<PatentApplicationDetail>("/patents/applications", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateApplication(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<CreateApplicationInput>) =>
      (await http.put<PatentApplicationDetail>(`/patents/applications/${id}`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdrawApplication(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (reason: string) =>
      (await http.post<PatentApplicationDetail>(`/patents/applications/${id}/withdraw`, { reason })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Director & Review ---------------------------------------------------------

export function useAssignDirector(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (director_id: number) =>
      (await http.post<PatentApplicationDetail>(`/patents/applications/${id}/assign-director`, { director_id })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReviewDecision(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { decision: "APPROVE" | "REJECT" | "REQUEST_REVISIONS"; justification: string }) =>
      (await http.post<ReviewDecision>(`/patents/applications/${id}/review-decision`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useFileAppeal(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (grounds: string) =>
      (await http.post<AppealRecord>(`/patents/applications/${id}/appeal`, { grounds })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAppealDecision(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { outcome: "REMAND" | "UPHOLD" | "MODIFY"; notes?: string }) =>
      (await http.post<AppealRecord>(`/patents/applications/${id}/appeal-decision`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Attorney & Assessment -----------------------------------------------------

export function useAssignAttorney(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (attorney_id: number) =>
      (await http.post<PatentApplicationDetail>(`/patents/applications/${id}/assign-attorney`, { attorney_id })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRespondAssignment(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (action: "accept" | "decline") =>
      (await http.post<PatentApplicationDetail>(`/patents/applications/${id}/respond-assignment`, { action })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAssessment(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (action: string = "start") =>
      (await http.post<PatentApplicationDetail>(`/patents/applications/${id}/assessment`, { action })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Budget & Maintenance ------------------------------------------------------

export function useBudgetDecision(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { decision: "APPROVE" | "REJECT"; notes?: string }) =>
      (await http.post<PatentApplicationDetail>(`/patents/applications/${id}/budget-decision`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRenewalDecision(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { renew: boolean; notes?: string }) =>
      (await http.post<PatentApplicationDetail>(`/patents/applications/${id}/renewal-decision`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Office Actions ------------------------------------------------------------

export function useOfficeActionResponse(actionId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { response_summary: string }) =>
      (await http.post(`/patents/office-actions/${actionId}/response`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Panels, Reports, Audit, Prior Art -----------------------------------------

export function useAttorneyPanel() {
  return useQuery({
    queryKey: keys.attorneyPanel(),
    queryFn: async () =>
      (await http.get<Page<AttorneyPanelMember>>("/patents/attorney-panel")).data,
    staleTime: 60_000,
  });
}

export function usePriorArtSearch() {
  return useMutation({
    mutationFn: async (query: string) =>
      (await http.post<PriorArtResult>("/patents/prior-art/search", { query })).data,
  });
}

export function useTechTransfer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      application_id: number;
      request_type: string;
      partner_name: string;
      terms_summary?: string;
    }) => (await http.post("/patents/tech-transfer", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReports() {
  return useQuery({
    queryKey: keys.reports(),
    queryFn: async () =>
      (await http.get<ReportsResponse>("/patents/reports")).data,
    staleTime: 30_000,
  });
}

export function useAuditLogs() {
  return useQuery({
    queryKey: keys.auditLogs(),
    queryFn: async () =>
      (await http.get<AuditLogsResponse>("/patents/audit-logs")).data,
    staleTime: 30_000,
  });
}
