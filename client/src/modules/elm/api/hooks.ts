import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  ApplyInput,
  HolidayItem,
  LeaveApplication,
  LeaveBalance,
  LeaveType,
  NotificationFeed,
  SlaConfiguration,
  SlaConfigurationInput,
  SlaEventItem,
  SlaRunCounters,
  WorkflowTaskItem,
} from "./types";

export function useLeaveTypes() {
  return useQuery({
    queryKey: ["elm", "types"],
    queryFn: async () => {
      const { data } = await http.get<LeaveType[]>("/elm/types");
      return data;
    },
  });
}

export function useLeaveBalances(year?: number) {
  return useQuery({
    queryKey: ["elm", "balances", year],
    queryFn: async () => {
      const { data } = await http.get<LeaveBalance[]>("/elm/balance", {
        params: year ? { year } : undefined,
      });
      return data;
    },
  });
}

export function useMyApplications() {
  return useQuery({
    queryKey: ["elm", "applications", "mine"],
    queryFn: async () => {
      const { data } = await http.get<LeaveApplication[]>("/elm/applications");
      return data;
    },
  });
}

export function useApplicationDetail(id: number) {
  return useQuery({
    queryKey: ["elm", "application", id],
    queryFn: async () => {
      const { data } = await http.get<LeaveApplication>(`/elm/applications/${id}`);
      return data;
    },
    enabled: Boolean(id),
  });
}

export function useSubstituteTasks() {
  return useQuery({
    queryKey: ["elm", "substitute", "tasks"],
    queryFn: async () => {
      const { data } = await http.get<LeaveApplication[]>("/elm/substitute/tasks");
      return data;
    },
  });
}

export interface PendingApprovalsData {
  unit_head: LeaveApplication[];
  establishment?: LeaveApplication[];
  sanction?: LeaveApplication[];
  director_self_sanction?: LeaveApplication[];
  cancellations: LeaveApplication[];
  resumptions: LeaveApplication[];
}

export function usePendingApprovals() {
  return useQuery({
    queryKey: ["elm", "approvals", "pending"],
    queryFn: async () => {
      const { data } = await http.get<PendingApprovalsData>("/elm/approvals/pending");
      return data;
    },
  });
}

export function useHolidayCalendar(year?: number) {
  return useQuery({
    queryKey: ["elm", "calendar", year],
    queryFn: async () => {
      const { data } = await http.get<HolidayItem[]>("/elm/calendar", {
        params: year ? { year } : undefined,
      });
      return data;
    },
  });
}

export function useApplyLeaveMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ApplyInput) => {
      const { data } = await http.post<LeaveApplication>("/elm/applications", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm", "applications"] });
      qc.invalidateQueries({ queryKey: ["elm", "balances"] });
    },
  });
}

export function useWithdrawMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (applicationId: number) => {
      const { data } = await http.post<LeaveApplication>(
        `/elm/applications/${applicationId}/withdraw`
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm", "applications"] });
      qc.invalidateQueries({ queryKey: ["elm", "balances"] });
    },
  });
}

export function useSubstituteRespondMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      applicationId,
      accept,
      declined_reason,
    }: {
      applicationId: number;
      accept: boolean;
      declined_reason?: string;
    }) => {
      const { data } = await http.post<LeaveApplication>(
        `/elm/applications/${applicationId}/substitute-respond`,
        { accept, declined_reason }
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm", "substitute"] });
      qc.invalidateQueries({ queryKey: ["elm", "approvals"] });
    },
  });
}

export function useUnitHeadReviewMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      applicationId,
      outcome,
      remarks,
      has_establishment_step,
    }: {
      applicationId: number;
      outcome: "RECOMMENDED" | "NOT_RECOMMENDED" | "APPROVE" | "REJECT";
      remarks?: string;
      has_establishment_step?: boolean;
    }) => {
      const { data } = await http.post<LeaveApplication>(
        `/elm/applications/${applicationId}/unit-head-review`,
        { outcome, remarks, has_establishment_step }
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm", "approvals"] });
      qc.invalidateQueries({ queryKey: ["elm", "applications"] });
      qc.invalidateQueries({ queryKey: ["elm", "balances"] });
    },
  });
}

export function useSanctionDecideMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      applicationId,
      approve,
      sanctioning_role,
      remarks,
    }: {
      applicationId: number;
      approve: boolean;
      sanctioning_role?: string;
      remarks?: string;
    }) => {
      const { data } = await http.post<LeaveApplication>(
        `/elm/applications/${applicationId}/sanction-decide`,
        { approve, sanctioning_role, remarks }
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm", "approvals"] });
      qc.invalidateQueries({ queryKey: ["elm", "applications"] });
      qc.invalidateQueries({ queryKey: ["elm", "balances"] });
    },
  });
}

export function useCancellationRequestMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      applicationId,
      reason,
    }: {
      applicationId: number;
      reason: string;
    }) => {
      const { data } = await http.post(
        `/elm/applications/${applicationId}/cancel-request`,
        { reason }
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm", "applications"] });
      qc.invalidateQueries({ queryKey: ["elm", "approvals"] });
    },
  });
}

export function useResumptionSubmitMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      applicationId,
      actual_resumption_date,
      reason_for_difference,
    }: {
      applicationId: number;
      actual_resumption_date: string;
      reason_for_difference?: string;
    }) => {
      const { data } = await http.post(
        `/elm/applications/${applicationId}/resume-submit`,
        { actual_resumption_date, reason_for_difference }
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm", "applications"] });
      qc.invalidateQueries({ queryKey: ["elm", "approvals"] });
    },
  });
}

export function useSlaConfigurations() {
  return useQuery({
    queryKey: ["elm", "sla", "config"],
    queryFn: async () => {
      const { data } = await http.get<SlaConfiguration[]>("/elm/admin/sla-config");
      return data;
    },
  });
}

export function useSlaConfigurationMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: SlaConfigurationInput) => {
      const { data } = await http.post<SlaConfiguration>("/elm/admin/sla-config", input);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm", "sla"] });
    },
  });
}

export function useSlaEvents(taskId?: number) {
  return useQuery({
    queryKey: ["elm", "sla", "events", taskId],
    queryFn: async () => {
      const { data } = await http.get<SlaEventItem[]>("/elm/admin/sla-events", {
        params: taskId ? { task_id: taskId } : undefined,
      });
      return data;
    },
  });
}

/** Trigger an SLA pass now instead of waiting for the scheduled sweep. */
export function useSlaProcessMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (taskIds?: number[]) => {
      const { data } = await http.post<SlaRunCounters>("/elm/admin/sla-process", {
        task_ids: taskIds ?? [],
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm", "sla"] });
      qc.invalidateQueries({ queryKey: ["elm", "notifications"] });
      qc.invalidateQueries({ queryKey: ["elm", "tasks"] });
    },
  });
}

export function useMyTasks() {
  return useQuery({
    queryKey: ["elm", "tasks", "mine"],
    queryFn: async () => {
      const { data } = await http.get<WorkflowTaskItem[]>("/elm/tasks/mine");
      return data;
    },
  });
}

export function useNotifications(unreadOnly = false) {
  return useQuery({
    queryKey: ["elm", "notifications", unreadOnly],
    queryFn: async () => {
      const { data } = await http.get<NotificationFeed>("/elm/notifications", {
        params: unreadOnly ? { unread: 1 } : undefined,
      });
      return data;
    },
  });
}

export function useMarkNotificationReadMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: number) => {
      const { data } = await http.post(`/elm/notifications/${notificationId}/read`, {});
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm", "notifications"] });
    },
  });
}
