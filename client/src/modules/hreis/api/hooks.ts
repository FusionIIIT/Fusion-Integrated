/** Data access hooks for the HR-EIS module. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  AppraisalSubmission,
  CpdaRequest,
  DashboardStats,
  EmployeeServiceRecord,
  HrAuditLog,
  HrNotification,
  LeaveRequest,
  LtcRequest,
  WorkflowConfiguration,
} from "./types";

const KEY = "hreis";

export const keys = {
  stats: () => [KEY, "stats"] as const,
  myRecord: () => [KEY, "service-records", "me"] as const,
  records: () => [KEY, "service-records"] as const,
  record: (id: number) => [KEY, "service-records", id] as const,
  leaves: () => [KEY, "leaves"] as const,
  leave: (id: number) => [KEY, "leaves", id] as const,
  appraisals: () => [KEY, "appraisals"] as const,
  appraisal: (id: number) => [KEY, "appraisals", id] as const,
  ltcList: () => [KEY, "ltc"] as const,
  ltc: (id: number) => [KEY, "ltc", id] as const,
  cpdaList: () => [KEY, "cpda"] as const,
  cpda: (id: number) => [KEY, "cpda", id] as const,
  workflows: () => [KEY, "workflows"] as const,
  auditLogs: () => [KEY, "audit-logs"] as const,
  notifications: () => [KEY, "notifications"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Dashboard Stats -----------------------------------------------------------
export function useDashboardStats() {
  return useQuery({
    queryKey: keys.stats(),
    queryFn: async () => (await http.get<DashboardStats>("/hreis/stats/")).data,
    staleTime: 30_000,
  });
}

// -- Service Records ----------------------------------------------------------
export function useMyServiceRecord() {
  return useQuery({
    queryKey: keys.myRecord(),
    queryFn: async () => (await http.get<EmployeeServiceRecord>("/hreis/service-records/me/")).data,
    staleTime: 60_000,
  });
}

export function useServiceRecords() {
  return useQuery({
    queryKey: keys.records(),
    queryFn: async () => (await http.get<EmployeeServiceRecord[]>("/hreis/service-records/")).data,
    staleTime: 30_000,
  });
}

export function useCreateServiceRecord() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<EmployeeServiceRecord>) =>
      (await http.post<EmployeeServiceRecord>("/hreis/service-records/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateServiceRecord() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: Partial<EmployeeServiceRecord> }) =>
      (await http.patch<EmployeeServiceRecord>(`/hreis/service-records/${id}/`, data)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Leaves -------------------------------------------------------------------
export function useLeaves() {
  return useQuery({
    queryKey: keys.leaves(),
    queryFn: async () => (await http.get<LeaveRequest[]>("/hreis/leaves/")).data,
    staleTime: 15_000,
  });
}

export function useLeave(id: number | undefined) {
  return useQuery({
    queryKey: keys.leave(id!),
    queryFn: async () => (await http.get<LeaveRequest>(`/hreis/leaves/${id}/`)).data,
    enabled: id != null,
  });
}

export function useApplyLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      leave_type: string;
      start_date: string;
      end_date: string;
      duration_days: number;
      justification: string;
    }) => (await http.post<LeaveRequest>("/hreis/leaves/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDecideLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, outcome, remarks }: { id: number; outcome: string; remarks: string }) =>
      (await http.post<LeaveRequest>(`/hreis/leaves/${id}/decide/`, { outcome, remarks })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Appraisals ---------------------------------------------------------------
export function useAppraisals() {
  return useQuery({
    queryKey: keys.appraisals(),
    queryFn: async () => (await http.get<AppraisalSubmission[]>("/hreis/appraisals/")).data,
    staleTime: 30_000,
  });
}

export function useAppraisal(id: number | undefined) {
  return useQuery({
    queryKey: keys.appraisal(id!),
    queryFn: async () => (await http.get<AppraisalSubmission>(`/hreis/appraisals/${id}/`)).data,
    enabled: id != null,
  });
}

export function useSubmitAppraisal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      academic_year,
      content,
      draft = false,
    }: {
      academic_year: string;
      content: Record<string, unknown>;
      draft?: boolean;
    }) =>
      (
        await http.post<AppraisalSubmission>(
          `/hreis/appraisals/${draft ? "?draft=1" : ""}`,
          { academic_year, content }
        )
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAssignReviewers() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reviewer_ids }: { id: number; reviewer_ids: number[] }) =>
      (await http.post<AppraisalSubmission>(`/hreis/appraisals/${id}/assign-reviewers/`, { reviewer_ids })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitAppraisalReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, score, comments }: { id: number; score: number; comments: string }) =>
      (await http.post<AppraisalSubmission>(`/hreis/appraisals/${id}/review/`, { score, comments })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useFinalizeAppraisal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, final_score, final_remarks }: { id: number; final_score: number; final_remarks: string }) =>
      (await http.post<AppraisalSubmission>(`/hreis/appraisals/${id}/finalize/`, { final_score, final_remarks })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- LTC ----------------------------------------------------------------------
export function useLtcClaims() {
  return useQuery({
    queryKey: keys.ltcList(),
    queryFn: async () => (await http.get<LtcRequest[]>("/hreis/ltc/")).data,
    staleTime: 15_000,
  });
}

export function useLtcClaim(id: number | undefined) {
  return useQuery({
    queryKey: keys.ltc(id!),
    queryFn: async () => (await http.get<LtcRequest>(`/hreis/ltc/${id}/`)).data,
    enabled: id != null,
  });
}

export function useSubmitLtc() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      request_type: string;
      block_year: string;
      travel_from: string;
      travel_to: string;
      travel_start_date: string;
      travel_end_date: string;
      estimated_amount: number;
      claimed_amount?: number;
      supporting_documents?: Array<{ name: string; url: string }>;
    }) => (await http.post<LtcRequest>("/hreis/ltc/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useVerifyLtc() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, verdict, remarks }: { id: number; verdict: string; remarks: string }) =>
      (await http.post<LtcRequest>(`/hreis/ltc/${id}/verify/`, { verdict, remarks })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDecideLtc() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, outcome, remarks }: { id: number; outcome: string; remarks: string }) =>
      (await http.post<LtcRequest>(`/hreis/ltc/${id}/decide/`, { outcome, remarks })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSettleLtc() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      passed_amount,
      reference_id,
      remarks,
    }: {
      id: number;
      passed_amount: number;
      reference_id: string;
      remarks?: string;
    }) => (await http.post<LtcRequest>(`/hreis/ltc/${id}/settle/`, { passed_amount, reference_id, remarks })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- CPDA ---------------------------------------------------------------------
export function useCpdaClaims() {
  return useQuery({
    queryKey: keys.cpdaList(),
    queryFn: async () => (await http.get<CpdaRequest[]>("/hreis/cpda/")).data,
    staleTime: 15_000,
  });
}

export function useCpdaClaim(id: number | undefined) {
  return useQuery({
    queryKey: keys.cpda(id!),
    queryFn: async () => (await http.get<CpdaRequest>(`/hreis/cpda/${id}/`)).data,
    enabled: id != null,
  });
}

export function useSubmitCpda() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      request_type: string;
      purpose: string;
      amount: number;
      supporting_documents?: unknown[];
    }) => (await http.post<CpdaRequest>("/hreis/cpda/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useVerifyCpda() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, verdict, remarks }: { id: number; verdict: string; remarks: string }) =>
      (await http.post<CpdaRequest>(`/hreis/cpda/${id}/verify/`, { verdict, remarks })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDecideCpda() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, outcome, remarks }: { id: number; outcome: string; remarks: string }) =>
      (await http.post<CpdaRequest>(`/hreis/cpda/${id}/decide/`, { outcome, remarks })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSettleCpda() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      passed_amount,
      voucher_no,
      remarks,
    }: {
      id: number;
      passed_amount: number;
      voucher_no: string;
      remarks?: string;
    }) => (await http.post<CpdaRequest>(`/hreis/cpda/${id}/settle/`, { passed_amount, voucher_no, remarks })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Workflow Settings ---------------------------------------------------------
export function useWorkflowConfigs() {
  return useQuery({
    queryKey: keys.workflows(),
    queryFn: async () => (await http.get<WorkflowConfiguration[]>("/hreis/workflows/settings/")).data,
    staleTime: 60_000,
  });
}

export function useUpdateWorkflowConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      setting_key,
      setting_value,
      description,
    }: {
      setting_key: string;
      setting_value: Record<string, unknown>;
      description?: string;
    }) => (await http.put("/hreis/workflows/settings/", { setting_key, setting_value, description })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Audit Logs ----------------------------------------------------------------
export function useAuditLogs() {
  return useQuery({
    queryKey: keys.auditLogs(),
    queryFn: async () => (await http.get<HrAuditLog[]>("/hreis/audit-logs/")).data,
    staleTime: 30_000,
  });
}

// -- Notifications ------------------------------------------------------------
export function useNotifications() {
  return useQuery({
    queryKey: keys.notifications(),
    queryFn: async () => (await http.get<HrNotification[]>("/hreis/notifications/")).data,
    staleTime: 10_000,
  });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await http.patch(`/hreis/notifications/${id}/read/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}
