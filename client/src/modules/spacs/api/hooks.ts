/** Data access for the SPACS module. */

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  ApplicationTransition,
  AwardCycle,
  CatalogueEntry,
  Page,
  ScholarshipApplication,
  SpacsAuditLog,
} from "./types";

const KEY = "spacs";

export const keys = {
  catalogue: (f?: unknown) => [KEY, "catalogue", f] as const,
  catalogueDetail: (id: number) => [KEY, "catalogue", id] as const,
  myApplications: () => [KEY, "applications", "mine"] as const,
  applicationDetail: (id: number) => [KEY, "application", id] as const,
  applicationTimeline: (id: number) => [KEY, "application", id, "timeline"] as const,
  verificationQueue: () => [KEY, "verification", "queue"] as const,
  decisionQueue: () => [KEY, "decision", "queue"] as const,
  awardCycles: () => [KEY, "awards", "cycles"] as const,
  awardCycleDetail: (id: number) => [KEY, "awards", "cycle", id] as const,
  publicAwards: () => [KEY, "awards", "public"] as const,
  auditTrail: (f?: unknown) => [KEY, "audit", f] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Catalogue -----------------------------------------------------------------
export function useCatalogueList(filters?: { type?: string; status?: string; program?: string }) {
  return useQuery({
    queryKey: keys.catalogue(filters),
    queryFn: () => http.get<Page<CatalogueEntry>>("/api/v1/spacs/catalogue", filters),
  });
}

export function useCatalogueDetail(id: number) {
  return useQuery({
    queryKey: keys.catalogueDetail(id),
    queryFn: () => http.get<CatalogueEntry>(`/api/v1/spacs/catalogue/${id}`),
    enabled: id > 0,
  });
}

export function useCreatePolicyVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ entryId, payload }: { entryId: number; payload: Record<string, unknown> }) =>
      http.post<Record<string, unknown>>(`/api/v1/spacs/catalogue/${entryId}/versions`, payload),
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublishCatalogue() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ versionId, payload }: { versionId: number; payload?: Record<string, unknown> }) =>
      http.post<Record<string, unknown>>(`/api/v1/spacs/catalogue/versions/${versionId}/publish`, payload ?? {}),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRetireCatalogue() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ entryId, reason }: { entryId: number; reason: string }) =>
      http.post<Record<string, unknown>>(`/api/v1/spacs/catalogue/${entryId}/retire`, { reason }),
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Applications -------------------------------------------------------------
export function useMyApplications() {
  return useQuery({
    queryKey: keys.myApplications(),
    queryFn: () => http.get<Page<ScholarshipApplication>>("/api/v1/spacs/applications/mine"),
  });
}

export function useApplicationDetail(id: number) {
  return useQuery({
    queryKey: keys.applicationDetail(id),
    queryFn: () => http.get<ScholarshipApplication>(`/api/v1/spacs/applications/${id}`),
    enabled: id > 0,
  });
}

export function useApplicationTimeline(id: number) {
  return useQuery({
    queryKey: keys.applicationTimeline(id),
    queryFn: () => http.get<ApplicationTransition[]>(`/api/v1/spacs/applications/${id}/timeline`),
    enabled: id > 0,
  });
}

export function useSaveDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { application_id?: number; catalogue_version_id?: number; form_data?: Record<string, unknown> }) =>
      http.post<ScholarshipApplication>("/api/v1/spacs/applications/draft", payload),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      http.post<ScholarshipApplication>(`/api/v1/spacs/applications/${id}/submit`, {}),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdrawApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason?: string }) =>
      http.post<ScholarshipApplication>(`/api/v1/spacs/applications/${id}/withdraw`, { reason }),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useInitiateRenewal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, targetAcademicYear }: { id: number; targetAcademicYear: string }) =>
      http.post<ScholarshipApplication>(`/api/v1/spacs/applications/${id}/renew`, {
        target_academic_year: targetAcademicYear,
      }),
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Verification & Decisions --------------------------------------------------
export function useVerificationQueue() {
  return useQuery({
    queryKey: keys.verificationQueue(),
    queryFn: () => http.get<Page<ScholarshipApplication>>("/api/v1/spacs/verification/queue"),
  });
}

export function useVerificationAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      applicationId,
      action,
      comments,
    }: {
      applicationId: number;
      action: "mark_verified" | "flag_concern" | "request_correction";
      comments?: string;
    }) =>
      http.post<ScholarshipApplication>(`/api/v1/spacs/verification/${applicationId}/action`, {
        action,
        comments,
      }),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useVerifyDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      docId,
      status,
      finding,
    }: {
      docId: number;
      status: "verified" | "flagged" | "rejected";
      finding?: string;
    }) =>
      http.post<Record<string, unknown>>(`/api/v1/spacs/verification/documents/${docId}`, {
        status,
        finding,
      }),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDecisionQueue() {
  return useQuery({
    queryKey: keys.decisionQueue(),
    queryFn: () => http.get<Page<ScholarshipApplication>>("/api/v1/spacs/decisions/queue"),
  });
}

export function useDecisionAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      applicationId,
      action,
      reason,
    }: {
      applicationId: number;
      action: "approve" | "reject" | "return";
      reason: string;
    }) =>
      http.post<ScholarshipApplication>(`/api/v1/spacs/decisions/${applicationId}/action`, {
        action,
        reason,
      }),
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Awards --------------------------------------------------------------------
export function useAwardCycles() {
  return useQuery({
    queryKey: keys.awardCycles(),
    queryFn: () => http.get<Page<AwardCycle>>("/api/v1/spacs/awards/cycles"),
  });
}

export function usePreparePool() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      cycleId,
      cpiThreshold,
    }: {
      cycleId: number;
      cpiThreshold?: string;
    }) =>
      http.post<Record<string, unknown>>(`/api/v1/spacs/awards/cycles/${cycleId}/pool`, {
        cpi_threshold: cpiThreshold,
      }),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAwardEvaluation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      cycleId,
      evaluations,
    }: {
      cycleId: number;
      evaluations: Array<{ candidate_id: number; score?: string; notes?: string; merit_rank?: number }>;
    }) =>
      http.post<Record<string, unknown>>(`/api/v1/spacs/awards/cycles/${cycleId}/evaluations`, {
        evaluations,
      }),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAwardApproval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      cycleId,
      decision,
      selectedCandidateIds,
      notes,
    }: {
      cycleId: number;
      decision: "approve" | "return";
      selectedCandidateIds?: number[];
      notes?: string;
    }) =>
      http.post<Record<string, unknown>>(`/api/v1/spacs/awards/cycles/${cycleId}/approve`, {
        decision,
        selected_candidate_ids: selectedCandidateIds,
        notes,
      }),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAwardPublish() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cycleId: number) =>
      http.post<Record<string, unknown>>(`/api/v1/spacs/awards/cycles/${cycleId}/publish`, {}),
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublicAwards(filters?: { year?: string }) {
  return useQuery({
    queryKey: [KEY, "awards", "public", filters],
    queryFn: () => http.get<Record<string, unknown>>("/api/v1/spacs/awards/public", filters),
  });
}

// -- Audit ---------------------------------------------------------------------
export function useAuditTrail(filters?: { event_type?: string; target_model?: string }) {
  return useQuery({
    queryKey: keys.auditTrail(filters),
    queryFn: () => http.get<Page<SpacsAuditLog>>("/api/v1/spacs/audit/trail", filters),
  });
}
