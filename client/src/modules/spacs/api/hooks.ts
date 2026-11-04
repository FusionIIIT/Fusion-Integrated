
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
  ScholarshipApplication,
  SpacsAuditLog,
} from "./types";

const KEY = "spacs";

export const keys = {
  catalogue: (f?: unknown) => [KEY, "catalogue", f] as const,
  catalogueDetail: (id: number) => [KEY, "catalogue", id] as const,
  myApplications: () => [KEY, "applications", "mine"] as const,
  applicationDetail: (id: number) => [KEY, "application", id] as const,
  applicationTimeline: (id: number) =>
    [KEY, "application", id, "timeline"] as const,
  verificationQueue: () => [KEY, "verification", "queue"] as const,
  decisionQueue: () => [KEY, "decision", "queue"] as const,
  awardCycles: () => [KEY, "awards", "cycles"] as const,
  awardCycleDetail: (id: number) =>
    [KEY, "awards", "cycle", id] as const,
  publicAwards: () => [KEY, "awards", "public"] as const,
  auditTrail: (f?: unknown) => [KEY, "audit", f] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -----------------------------------------------------------------------------
// Catalogue
// -----------------------------------------------------------------------------

export function useCatalogueList(
  filters?: { type?: string; status?: string; program?: string }
) {
  return useQuery({
    queryKey: keys.catalogue(filters),
    queryFn: () =>
      http.get<CatalogueEntry[]>("/api/v1/spacs/catalogue", {
  params: filters,
}),
  });
}

export function useCatalogueDetail(id: number) {
  return useQuery({
    queryKey: keys.catalogueDetail(id),
    queryFn: () =>
      http.get<CatalogueEntry>(`/api/v1/spacs/catalogue/${id}`),
    enabled: id > 0,
  });
}

export function useCreatePolicyVersion() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      entryId,
      payload,
    }: {
      entryId: number;
      payload: Record<string, unknown>;
    }) =>
      http.post<Record<string, unknown>>(
        `/api/v1/spacs/catalogue/${entryId}/versions`,
        payload
      ),
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublishCatalogue() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      versionId,
      payload,
    }: {
      versionId: number;
      payload: {
        policy_approval_ref: string;
        policy_approval_date: string;
      };
    }) =>
      http.post<Record<string, unknown>>(
        `/api/v1/spacs/catalogue/versions/${versionId}/publish`,
        payload
      ),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRetireCatalogue() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      entryId,
    }: {
      entryId: number;
    }) =>
      http.post<Record<string, unknown>>(
        `/api/v1/spacs/catalogue/${entryId}/retire`,
        {}
      ),
    onSuccess: () => invalidateAll(qc),
  });
}

// -----------------------------------------------------------------------------
// Applications
// -----------------------------------------------------------------------------

export function useMyApplications() {
  return useQuery({
    queryKey: keys.myApplications(),
    queryFn: () =>
      http.get<ScholarshipApplication[]>(
        "/api/v1/spacs/applications/mine"
      ),
  });
}

export function useApplicationDetail(id: number) {
  return useQuery({
    queryKey: keys.applicationDetail(id),
    queryFn: () =>
      http.get<ScholarshipApplication>(
        `/api/v1/spacs/applications/${id}`
      ),
    enabled: id > 0,
  });
}

export function useApplicationTimeline(id: number) {
  return useQuery({
    queryKey: keys.applicationTimeline(id),
    queryFn: () =>
      http.get<{
        application_id: number;
        timeline: ApplicationTransition[];
      }>(`/api/v1/spacs/applications/${id}/timeline`),
    enabled: id > 0,
  });
}

export function useSaveDraft() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (payload: {
      application_id?: number;
      policy_version_id: number;
      academic_cycle: string;
      submission_data: Record<string, unknown>;
      documents?: Record<string, unknown>[];
      applicant_snapshot?: Record<string, unknown>;
    }) =>
      http.post<ScholarshipApplication>(
        "/api/v1/spacs/applications/draft",
        payload
      ),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitApplication() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      studentSnapshot,
    }: {
      id: number;
      studentSnapshot?: Record<string, unknown>;
    }) =>
      http.post<ScholarshipApplication>(
        `/api/v1/spacs/applications/${id}/submit`,
        {
          student_snapshot: studentSnapshot ?? {},
        }
      ),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdrawApplication() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      reason,
    }: {
      id: number;
      reason?: string;
    }) =>
      http.post<ScholarshipApplication>(
        `/api/v1/spacs/applications/${id}/withdraw`,
        { reason }
      ),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useInitiateRenewal() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      academicCycle,
      policyVersionId,
    }: {
      id: number;
      academicCycle: string;
      policyVersionId: number;
    }) =>
      http.post<ScholarshipApplication>(
        `/api/v1/spacs/applications/${id}/renew`,
        {
          academic_cycle: academicCycle,
          policy_version_id: policyVersionId,
        }
      ),
    onSuccess: () => invalidateAll(qc),
  });
}

// -----------------------------------------------------------------------------
// Verification
// -----------------------------------------------------------------------------

export function useVerificationQueue() {
  return useQuery({
    queryKey: keys.verificationQueue(),
    queryFn: () =>
      http.get<ScholarshipApplication[]>(
        "/api/v1/spacs/verification/queue"
      ),
  });
}

export function useVerificationAction() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      applicationId,
      action,
      comment,
      findings,
    }: {
      applicationId: number;
      action: "verify" | "flag_concern" | "request_correction";
      comment?: string;
      findings?: Record<string, unknown>;
    }) =>
      http.post<ScholarshipApplication>(
        `/api/v1/spacs/verification/${applicationId}/action`,
        {
          action,
          comment,
          findings,
        }
      ),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useVerifyDocument() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      docId,
      status,
      comment,
    }: {
      docId: number;
      status: string;
      comment?: string;
    }) =>
      http.post<Record<string, unknown>>(
        `/api/v1/spacs/verification/documents/${docId}`,
        {
          status,
          comment,
        }
      ),
    onSuccess: () => invalidateAll(qc),
  });
}

// -----------------------------------------------------------------------------
// Convener decisions
// -----------------------------------------------------------------------------

export function useDecisionQueue() {
  return useQuery({
    queryKey: keys.decisionQueue(),
    queryFn: () =>
      http.get<ScholarshipApplication[]>(
        "/api/v1/spacs/decisions/queue"
      ),
  });
}

export function useDecisionAction() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      applicationId,
      outcome,
      reason,
      policyReference,
    }: {
      applicationId: number;
      outcome:
        | "approved"
        | "rejected"
        | "return_for_correction";
      reason: string;
      policyReference?: string;
    }) =>
      http.post<ScholarshipApplication>(
        `/api/v1/spacs/decisions/${applicationId}/action`,
        {
          outcome,
          reason,
          policy_reference: policyReference,
        }
      ),
    onSuccess: () => invalidateAll(qc),
  });
}

// -----------------------------------------------------------------------------
// Convocation awards
// -----------------------------------------------------------------------------

export function useAwardCycles() {
  return useQuery({
    queryKey: keys.awardCycles(),
    queryFn: () =>
      http.get<AwardCycle[]>("/api/v1/spacs/awards/cycles"),
  });
}

export function usePreparePool() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      cycleId,
      candidateUserIds,
      snapshots,
    }: {
      cycleId: number;
      candidateUserIds: number[];
      snapshots?: Record<string, Record<string, unknown>>;
    }) =>
      http.post<Record<string, unknown>>(
        `/api/v1/spacs/awards/cycles/${cycleId}/pool`,
        {
          candidate_user_ids: candidateUserIds,
          snapshots: snapshots ?? {},
        }
      ),
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
      evaluations: Array<{
        candidate_id: number;
        score?: string;
        notes?: string;
        merit_rank?: number;
      }>;
    }) =>
      http.post<AwardCycle>(
        `/api/v1/spacs/awards/cycles/${cycleId}/evaluation`,
        {
          evaluations,
        }
      ),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAwardApproval() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      cycleId,
      approvalAuthority,
      approvalReference,
      winningCandidateIds,
    }: {
      cycleId: number;
      approvalAuthority: string;
      approvalReference: string;
      winningCandidateIds: number[];
    }) =>
      http.post<AwardCycle>(
        `/api/v1/spacs/awards/cycles/${cycleId}/approval`,
        {
          approval_authority: approvalAuthority,
          approval_reference: approvalReference,
          winning_candidate_ids: winningCandidateIds,
        }
      ),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAwardPublish() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (cycleId: number) =>
      http.post<AwardCycle>(
        `/api/v1/spacs/awards/cycles/${cycleId}/publish`,
        {}
      ),
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublicAwards(filters?: { year?: string }) {
  return useQuery({
    queryKey: [KEY, "awards", "public", filters],
    queryFn: () =>
     http.get<Record<string, unknown>[]>(
  "/api/v1/spacs/awards/public",
  { params: filters }
),
  });
}

// -----------------------------------------------------------------------------
// Audit
// -----------------------------------------------------------------------------

export function useAuditTrail(filters?: {
  entity_type?: string;
  entity_id?: number;
  actor_user_id?: number;
  action?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: keys.auditTrail(filters),
    queryFn: () =>
      http.get<SpacsAuditLog[]>(
  "/api/v1/spacs/audit/trail",
  { params: filters }
),
  });
}
