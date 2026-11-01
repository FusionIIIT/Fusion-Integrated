/** React Query hooks for Patent Management System.
 *
 *  Provides typed data access, cache management, and mutation invalidation.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type {
  ApplicationDocument,
  AttorneyAssignment,
  AttorneyPanel,
  DirectorReview,
  ExtensionRequest,
  ExternalFilingRecord,
  InventorInput,
  LicensingRequest,
  MaintenanceSchedule,
  OfficeAction,
  OfficeActionResponse,
  Page,
  PatentAppeal,
  PatentApplicationDetail,
  PatentApplicationListItem,
  PatentAuditLog,
  PatentBudget,
  PortfolioAnalytics,
  PostGrantPatent,
  PriorArtSearchRecord,
  RenewalDecision,
} from "./types";

const MODULE_KEY = "pms";

export const keys = {
  applications: (filters?: unknown) => [MODULE_KEY, "applications", filters] as const,
  application: (id: number) => [MODULE_KEY, "application", id] as const,
  history: (id: number) => [MODULE_KEY, "history", id] as const,
  documents: (appId: number) => [MODULE_KEY, "documents", appId] as const,
  reviews: () => [MODULE_KEY, "reviews"] as const,
  attorneyAssignments: () => [MODULE_KEY, "attorney-assignments"] as const,
  attorneyPanels: () => [MODULE_KEY, "attorney-panels"] as const,
  officeActions: (filters?: unknown) => [MODULE_KEY, "office-actions", filters] as const,
  maintenance: (filters?: unknown) => [MODULE_KEY, "maintenance", filters] as const,
  licensing: (filters?: unknown) => [MODULE_KEY, "licensing", filters] as const,
  appeals: (filters?: unknown) => [MODULE_KEY, "appeals", filters] as const,
  priorArt: (filters?: unknown) => [MODULE_KEY, "prior-art", filters] as const,
  analytics: () => [MODULE_KEY, "analytics"] as const,
  auditLogs: (filters?: unknown) => [MODULE_KEY, "audit-logs", filters] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [MODULE_KEY] });
}

// --- Applications -------------------------------------------------------------

export function useApplications(filters?: { status?: string; domain?: string; search?: string }) {
  return useQuery({
    queryKey: keys.applications(filters),
    queryFn: async () =>
      (await http.get<Page<PatentApplicationListItem>>("/pms/applications", { params: filters }))
        .data,
    staleTime: 30_000,
  });
}

export function useApplication(id: number | undefined) {
  return useQuery({
    queryKey: keys.application(id ?? 0),
    queryFn: async () => (await http.get<PatentApplicationDetail>(`/pms/applications/${id}`)).data,
    enabled: typeof id === "number" && id > 0,
    staleTime: 10_000,
  });
}

export function useApplicationHistory(id: number | undefined) {
  return useQuery({
    queryKey: keys.history(id ?? 0),
    queryFn: async () =>
      (await http.get<Page<PatentAuditLog>>(`/pms/applications/${id}/history`)).data,
    enabled: typeof id === "number" && id > 0,
    staleTime: 10_000,
  });
}

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      title: string;
      abstract: string;
      description: string;
      claims: string;
      domain: string;
      filing_type?: string;
      is_confidential?: boolean;
      inventors: InventorInput[];
    }) => (await http.post<PatentApplicationDetail>("/pms/applications", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateApplication(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      title?: string;
      abstract?: string;
      description?: string;
      claims?: string;
      domain?: string;
      filing_type?: string;
      is_confidential?: boolean;
      inventors?: InventorInput[];
    }) => (await http.put<PatentApplicationDetail>(`/pms/applications/${id}`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdrawApplication(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload?: { reason?: string }) =>
      (await http.post<{ status: string }>(`/pms/applications/${id}/withdraw`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// --- Documents ----------------------------------------------------------------

export function useDocuments(applicationId: number | undefined) {
  return useQuery({
    queryKey: keys.documents(applicationId ?? 0),
    queryFn: async () =>
      (await http.get<Page<ApplicationDocument>>(`/pms/applications/${applicationId}/documents`)).data,
    enabled: typeof applicationId === "number" && applicationId > 0,
    staleTime: 30_000,
  });
}

export function useUploadDocument(applicationId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      file,
      document_type,
      title,
      sensitivity = "internal",
    }: {
      file: File;
      document_type: string;
      title: string;
      sensitivity?: string;
    }) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("document_type", document_type);
      formData.append("title", title);
      formData.append("sensitivity", sensitivity);
      return (
        await http.post<ApplicationDocument>(
          `/pms/applications/${applicationId}/documents`,
          formData,
          { headers: { "Content-Type": "multipart/form-data" } }
        )
      ).data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export async function downloadDocument(documentId: number, fallbackFilename: string) {
  try {
    const res = await http.get(`/pms/documents/${documentId}/download`, {
      responseType: "blob",
    });
    const filename = filenameFromDisposition(res.headers["content-disposition"], fallbackFilename);
    saveBlob(res.data, filename);
  } catch (e) {
    await readBlobError(e);
    throw e;
  }
}

// --- Director Reviews ---------------------------------------------------------

export function useReviewQueue() {
  return useQuery({
    queryKey: keys.reviews(),
    queryFn: async () =>
      (await http.get<Page<PatentApplicationListItem>>("/pms/reviews")).data,
    staleTime: 15_000,
  });
}

export function useAssignDirector(applicationId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { director_user_id: number; due_days?: number }) =>
      (await http.post<{ detail: string }>(`/pms/applications/${applicationId}/assign-director`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitDirectorReview(applicationId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { decision: string; justification: string }) =>
      (await http.post<DirectorReview>(`/pms/applications/${applicationId}/review`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// --- Attorney Panels & Prosecution -------------------------------------------

export function useAttorneyAssignments() {
  return useQuery({
    queryKey: keys.attorneyAssignments(),
    queryFn: async () =>
      (await http.get<Page<AttorneyAssignment>>("/pms/attorney/assignments")).data,
    staleTime: 15_000,
  });
}

export function useAttorneyPanels() {
  return useQuery({
    queryKey: keys.attorneyPanels(),
    queryFn: async () =>
      (await http.get<Page<AttorneyPanel>>("/pms/attorney-panels")).data,
    staleTime: 60_000,
  });
}

export function useCreateAttorneyPanel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      user_id: number;
      name: string;
      firm_name: string;
      email: string;
      specialization: string;
      max_workload: number;
      is_active?: boolean;
    }) => (await http.post<AttorneyPanel>("/pms/attorney-panels", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAssignAttorney(applicationId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { attorney_user_id: number; instructions?: string }) =>
      (await http.post<AttorneyAssignment>(`/pms/applications/${applicationId}/assign-attorney`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRespondAttorneyAssignment(assignmentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { accept: boolean; remarks?: string }) =>
      (await http.post<AttorneyAssignment>(`/pms/assignments/${assignmentId}/respond`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// --- Budgeting & Filing -------------------------------------------------------

export function useApproveBudget(applicationId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      filing_fees: string;
      attorney_fees: string;
      administrative_costs: string;
      justification?: string;
    }) => (await http.post<PatentBudget>(`/pms/applications/${applicationId}/budget`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRecordFiling(applicationId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      jurisdiction: string;
      filing_number: string;
      filing_date: string;
      patent_office: string;
      confirmation_details?: string;
      international_justification?: string;
    }) => (await http.post<ExternalFilingRecord>(`/pms/applications/${applicationId}/record-filing`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// --- Office Actions -----------------------------------------------------------

export function useOfficeActions(filters?: { application_id?: number; status?: string }) {
  return useQuery({
    queryKey: keys.officeActions(filters),
    queryFn: async () =>
      (await http.get<Page<OfficeAction>>("/pms/office-actions", { params: filters })).data,
    staleTime: 15_000,
  });
}

export function useRecordOfficeAction(applicationId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      action_number: string;
      action_type: string;
      issue_date: string;
      response_deadline: string;
      description: string;
    }) => (await http.post<OfficeAction>(`/pms/applications/${applicationId}/office-actions`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDraftOfficeActionResponse(actionId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { draft_text: string; requires_applicant_approval?: boolean }) =>
      (await http.post<OfficeActionResponse>(`/pms/office-actions/${actionId}/responses`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useApproveOfficeActionResponse(responseId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      (await http.post<OfficeActionResponse>(`/pms/office-actions/responses/${responseId}/approve`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitOfficeActionResponse(responseId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload?: { submission_details?: string }) =>
      (await http.post<OfficeActionResponse>(`/pms/office-actions/responses/${responseId}/submit`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRequestOfficeActionExtension(actionId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { requested_days: number; reason: string }) =>
      (await http.post<ExtensionRequest>(`/pms/office-actions/${actionId}/extensions`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDecideOfficeActionExtension(extensionId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { is_granted: boolean; new_deadline?: string }) =>
      (await http.post<ExtensionRequest>(`/pms/office-actions/extensions/${extensionId}/decide`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// --- Post-Grant & Maintenance -------------------------------------------------

export function useGrantPatent(applicationId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      grant_number: string;
      grant_date: string;
      patent_document_url?: string;
    }) => (await http.post<PostGrantPatent>(`/pms/applications/${applicationId}/grant`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useMaintenanceSchedules(filters?: { post_grant_id?: number; status?: string }) {
  return useQuery({
    queryKey: keys.maintenance(filters),
    queryFn: async () =>
      (await http.get<Page<MaintenanceSchedule>>("/pms/maintenance", { params: filters })).data,
    staleTime: 30_000,
  });
}

export function useRequestMaintenanceDecision(scheduleId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      (await http.post<MaintenanceSchedule>(`/pms/maintenance/${scheduleId}/request-decision`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDecideMaintenanceRenewal(scheduleId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { decision: "renew" | "do_not_renew"; justification: string }) =>
      (await http.post<RenewalDecision>(`/pms/maintenance/${scheduleId}/decide`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRecordMaintenancePayment(scheduleId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { payment_reference: string; paid_amount?: string }) =>
      (await http.post<MaintenanceSchedule>(`/pms/maintenance/${scheduleId}/pay`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// --- Licensing & Appeals ------------------------------------------------------

export function useLicensingRequests(filters?: { application_id?: number; status?: string }) {
  return useQuery({
    queryKey: keys.licensing(filters),
    queryFn: async () =>
      (await http.get<Page<LicensingRequest>>("/pms/licensing", { params: filters })).data,
    staleTime: 30_000,
  });
}

export function useCreateLicensingRequest(applicationId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      licensee_name: string;
      licensee_contact: string;
      license_type: string;
      proposed_terms: string;
      royalty_rate: string;
      financial_terms?: string;
    }) => (await http.post<LicensingRequest>(`/pms/applications/${applicationId}/licensing`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReviewLicensingRequest(requestId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { decision: "approved" | "rejected"; review_notes: string }) =>
      (await http.post<LicensingRequest>(`/pms/licensing/${requestId}/review`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAppeals(filters?: { application_id?: number }) {
  return useQuery({
    queryKey: keys.appeals(filters),
    queryFn: async () =>
      (await http.get<Page<PatentAppeal>>("/pms/appeals", { params: filters })).data,
    staleTime: 30_000,
  });
}

export function useCreateAppeal(applicationId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { grounds: string; justification: string }) =>
      (await http.post<PatentAppeal>(`/pms/applications/${applicationId}/appeals`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRecordAppealOutcome(appealId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { outcome: "allowed" | "dismissed"; justification: string }) =>
      (await http.post<PatentAppeal>(`/pms/appeals/${appealId}/outcome`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// --- Prior Art Searches -------------------------------------------------------

export function usePriorArtSearches(filters?: { application_id?: number }) {
  return useQuery({
    queryKey: keys.priorArt(filters),
    queryFn: async () =>
      (await http.get<Page<PriorArtSearchRecord>>("/pms/prior-art", { params: filters })).data,
    staleTime: 30_000,
  });
}

export function useRecordPriorArtSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      application_id?: number;
      query_string: string;
      databases_searched: string[];
      results_count: number;
      session_notes?: string;
    }) => (await http.post<PriorArtSearchRecord>("/pms/prior-art", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAttachPriorArt(searchId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { application_id: number; relevance_notes?: string }) =>
      (await http.post<{ detail: string }>(`/pms/prior-art/${searchId}/attach`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// --- Analytics & Audit --------------------------------------------------------

export function usePortfolioAnalytics() {
  return useQuery({
    queryKey: keys.analytics(),
    queryFn: async () => (await http.get<PortfolioAnalytics>("/pms/reports/analytics")).data,
    staleTime: 60_000,
  });
}

export function useAuditLogs(filters?: { application_id?: number; action_type?: string }) {
  return useQuery({
    queryKey: keys.auditLogs(filters),
    queryFn: async () =>
      (await http.get<Page<PatentAuditLog>>("/pms/audit-logs", { params: filters })).data,
    staleTime: 15_000,
  });
}
