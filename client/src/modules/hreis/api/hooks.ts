/** HR-EIS calls use the platform's credentialed HTTP client. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../../../auth/AuthProvider";
import { http } from "../../../lib/http";
import type {
  AppraisalDecisionInput, AppraisalInput, AssignReviewersInput, ClaimInput,
  ClaimReviewInput, CreateRecord,
  FinancialReviewInput, FinancialReviewRecord, FinancialProcessingInput,
  HRAudit, HRComplianceRequestStatus, HRNotification, HRPolicy,
  HRPolicyInput, HRRequest, HRRequestDetail, LeaveBalances, LeaveInput, Page, RequestDecisionInput,
  ServiceRecord, UpdateRecord, VerifiedLeaveCreditInput, VerifiedLeaveCreditRecord,
} from "./types";

const key = ["hreis"] as const;

// Session identity is part of every HR-EIS read cache key. A role switch (or
// another user signing in) cannot render data loaded for a different principal.
function useRoleQueryKey(...suffix: (string | number)[]) {
  const { session } = useAuth();
  return [...key, session?.user.id ?? null, session?.active_role ?? null, ...suffix];
}

function uniqueOperationKey(): string {
  return crypto.randomUUID();
}

export function useMyServiceRecord() {
  return useQuery({
    queryKey: useRoleQueryKey("my-record"),
    queryFn: async () =>
      (await http.get<ServiceRecord>("/hreis/service-records/me/")).data,
    retry: false,
  });
}

export function useServiceRecords() {
  return useQuery({
    queryKey: useRoleQueryKey("records"),
    queryFn: async () =>
      (await http.get<Page<ServiceRecord>>("/hreis/service-records/")).data,
  });
}

export function useRequests(view: "all" | "approvals" = "all") {
  return useQuery({
    queryKey: useRoleQueryKey("requests", view),
    queryFn: async () =>
      (await http.get<Page<HRRequest>>(
        view === "approvals" ? "/hreis/requests/approvals/" : "/hreis/requests/",
      )).data,
  });
}

export function useNotifications() {
  return useQuery({
    queryKey: useRoleQueryKey("notifications"),
    queryFn: async () =>
      (await http.get<Page<HRNotification>>("/hreis/notifications/")).data,
  });
}

export function useRequestDetails(id: number) {
  return useQuery({
    queryKey: useRoleQueryKey("request", id),
    queryFn: async () =>
      (await http.get<HRRequestDetail>(`/hreis/requests/${id}/`)).data,
    retry: false,
  });
}

export function useComplianceRequests() {
  return useQuery({
    queryKey: useRoleQueryKey("compliance-requests"),
    queryFn: async () =>
      (await http.get<Page<HRComplianceRequestStatus>>(
        "/hreis/compliance/requests/",
      )).data,
  });
}

export function useAuditEvents() {
  return useQuery({
    queryKey: useRoleQueryKey("audit"),
    queryFn: async () =>
      (await http.get<Page<HRAudit>>("/hreis/audit/")).data,
  });
}

export function useCreateServiceRecord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateRecord) =>
      (await http.post<ServiceRecord>("/hreis/service-records/", data, {
        headers: { "Idempotency-Key": uniqueOperationKey() },
      })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: key }),
  });
}

export function usePolicies(enabled = true) {
  return useQuery({
    queryKey: useRoleQueryKey("policies"),
    enabled,
    queryFn: async () => (await http.get<Page<HRPolicy>>("/hreis/policies/")).data,
  });
}

export function useOwnLeaveBalances() {
  return useQuery({ queryKey: useRoleQueryKey("balances"),
    queryFn: async () => (await http.get<LeaveBalances>("/hreis/leave/balances/")).data });
}

export function useServiceRecord(id: number) {
  return useQuery({ queryKey: useRoleQueryKey("record", id),
    queryFn: async () => (await http.get<ServiceRecord>(`/hreis/service-records/${id}/`)).data });
}

export function useComplianceRequest(id: number) {
  return useQuery({ queryKey: useRoleQueryKey("compliance", id),
    queryFn: async () => (await http.get<HRComplianceRequestStatus>(`/hreis/compliance/requests/${id}/`)).data });
}

export function useMarkNotificationRead() {
  return useAction<{ id: number }, HRNotification>(
    ({ id }) => `/hreis/notifications/${id}/read/`, () => ({}));
}

function useAction<TBody, TResult>(url: (body: TBody) => string,
                                    body: (data: TBody) => unknown) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: TBody) =>
      (await http.post<TResult>(url(data), body(data), {
        headers: { "Idempotency-Key": uniqueOperationKey() },
      })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: key }),
  });
}

export function useCreatePolicy() {
  return useAction<HRPolicyInput, HRPolicy>(
    () => "/hreis/policies/", (data) => data);
}

export function useRecordVerifiedLeaveCredit() {
  return useAction<VerifiedLeaveCreditInput, VerifiedLeaveCreditRecord>(
    () => "/hreis/leave-balances/credits/", (data) => data);
}

export function useSubmitLeave() {
  return useAction<LeaveInput, HRRequest>(
    () => "/hreis/requests/leave/", (data) => data);
}

export function useSubmitClaim() {
  return useAction<ClaimInput, HRRequest>(
    () => "/hreis/requests/claims/", (data) => data);
}

export function useSubmitAppraisal() {
  return useAction<AppraisalInput, HRRequest>(
    () => "/hreis/requests/appraisals/", (data) => data);
}

export function useVerifyClaim() {
  return useAction<ClaimReviewInput, HRRequest>(
    ({ id }) => `/hreis/requests/${id}/verify-claim/`,
    ({ document_review_reference, eligibility_basis }) =>
      ({ document_review_reference, eligibility_basis }));
}

export function useVerifyFinancialCorrectness() {
  return useAction<FinancialReviewInput, FinancialReviewRecord>(
    ({ id }) => `/hreis/requests/${id}/financial-review/`,
    ({ financial_review_reference }) => ({ financial_review_reference }),
  );
}

export function useRecordFinancialProcessing() {
  return useAction<FinancialProcessingInput, HRRequest>(
    ({ id }) => `/hreis/requests/${id}/financial-processing/`,
    ({ financial_review_reference, source_system, external_status_reference, payment_status }) =>
      ({ financial_review_reference, source_system, external_status_reference, payment_status }));
}

export function useDecideRequest() {
  return useAction<RequestDecisionInput, HRRequest>(
    ({ id }) => `/hreis/requests/${id}/decision/`,
    ({ event, reason }) => ({ event, reason }));
}

export function useAssignReviewers() {
  return useAction<AssignReviewersInput, HRRequest>(
    ({ id }) => `/hreis/requests/${id}/assign-reviewers/`,
    ({ reviewer_user_ids }) => ({ reviewer_user_ids }));
}

export function useDecideAppraisal() {
  return useAction<AppraisalDecisionInput, HRRequest>(
    ({ id }) => `/hreis/requests/${id}/appraisal-decision/`,
    ({ event }) => ({ event }));
}

export function useUpdateServiceRecord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, expected_revision, fields }: UpdateRecord) =>
      (await http.patch<ServiceRecord>(`/hreis/service-records/${id}/`, {
        expected_revision, ...fields,
      }, {
        headers: { "Idempotency-Key": uniqueOperationKey() },
      })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: key }),
  });
}
