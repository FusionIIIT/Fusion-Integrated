import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Appraisal, AppraisalWindow, AuditEvent, Claim, EmployeeRecord,
  HRNotification, Page, WorkflowRoute,
  LeaveRequest, ManagedLeaveBalance,
} from "./types";

const ROOT = "/hr";
const KEY = "hr-eis";

function useHRList<T>(path: string, key: string) {
  return useQuery({
    queryKey: [KEY, key],
    queryFn: async () => (await http.get<Page<T>>(`${ROOT}/${path}`)).data,
  });
}

function useHRMutation<T, B>(path: (body: B) => string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: B) =>
      (await http.post<T>(path(body), body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}

export const useEmployees = () =>
  useHRList<EmployeeRecord>("employees/", "employees");
export const useCreateEmployee = () =>
  useHRMutation<EmployeeRecord, Record<string, unknown>>(
    () => `${ROOT}/employees/create/`);

export const useClaims = () => useHRList<Claim>("claims/", "claims");
export const useSubmitClaim = () =>
  useHRMutation<Claim, Record<string, unknown>>(() => `${ROOT}/claims/create/`);
export const useVerifyClaim = (id: number) =>
  useHRMutation<Claim, { verified: boolean; note: string }>(
    () => `${ROOT}/claims/${id}/verify/`);
export const useDecideClaim = (id: number) =>
  useHRMutation<Claim, { action: string; note: string }>(
    () => `${ROOT}/claims/${id}/decision/`);
export const useProcessClaim = (id: number) =>
  useHRMutation<Claim, { financially_correct: boolean; details: Record<string, unknown> }>(
    () => `${ROOT}/claims/${id}/processing/`);
export const useRecordIntegration = (id: number) =>
  useHRMutation<unknown, Record<string, unknown>>(
    () => `${ROOT}/claims/${id}/integration-status/`);

export const useAppraisals = () =>
  useHRList<Appraisal>("appraisals/", "appraisals");
export const useSubmitAppraisal = () =>
  useHRMutation<Appraisal, Record<string, unknown>>(
    () => `${ROOT}/appraisals/create/`);
export const useAssignReviewers = (id: number) =>
  useHRMutation<Appraisal, { reviewer_user_ids: number[] }>(
    () => `${ROOT}/appraisals/${id}/reviewers/`);
export const useReviewAppraisal = (id: number) =>
  useHRMutation<Appraisal, { action: string; note: string }>(
    () => `${ROOT}/appraisals/${id}/review/`);

export const useWorkflowRoutes = () =>
  useHRList<WorkflowRoute>("workflow-routes/", "workflow-routes");
export const useSaveWorkflowRoute = () =>
  useHRMutation<WorkflowRoute, Record<string, unknown>>(
    () => `${ROOT}/workflow-routes/save/`);
export const useAppraisalWindows = () =>
  useHRList<AppraisalWindow>("appraisal-windows/", "appraisal-windows");
export const useSaveAppraisalWindow = () =>
  useHRMutation<AppraisalWindow, Record<string, unknown>>(
    () => `${ROOT}/appraisal-windows/save/`);
export const useAuditEvents = () =>
  useHRList<AuditEvent>("audit-events/", "audit-events");
export const useNotifications = () =>
  useHRList<HRNotification>("notifications/", "notifications");
export const usePublishNotice = () =>
  useHRMutation<{ published: number }, Record<string, unknown>>(
    () => `${ROOT}/notices/`);

export const useLeaveRequests = () =>
  useHRList<LeaveRequest>("leaves/", "leaves");
export const useSubmitLeaveRequest = () =>
  useHRMutation<LeaveRequest, {
    leave_type: string; duration_days: string; justification: string;
  }>(() => `${ROOT}/leaves/create/`);
export const useDecideLeaveRequest = (id: number) =>
  useHRMutation<LeaveRequest, { action: string; note: string }>(
    () => `${ROOT}/leaves/${id}/decision/`);
export const useManagedLeaveBalances = () =>
  useHRList<ManagedLeaveBalance>("leave-balances/", "leave-balances");
export const useSaveLeaveBalance = () =>
  useHRMutation<ManagedLeaveBalance, {
    employee_user_id: number; leave_type: string; available_days: string;
    is_eligible: boolean;
  }>(() => `${ROOT}/leave-balances/save/`);

export function useUpdateEmployeeRecord(userId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.patch<EmployeeRecord>(
        `${ROOT}/employees/${userId}/update/`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}
