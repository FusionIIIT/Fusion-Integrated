import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  ApplyLeavePayload,
  ApprovalStep,
  HolidayCalendarEntry,
  LeaveApplication,
  LeaveBalance,
  LeavePolicy,
} from "./types";

export function useLeaveBalances(year?: number) {
  return useQuery({
    queryKey: ["elm", "balances", year],
    queryFn: async () => {
      const res = await http.get<LeaveBalance[]>("/elm/balances/", {
        params: year ? { year } : {},
      });
      return res.data;
    },
  });
}

export function useLeavePolicies() {
  return useQuery({
    queryKey: ["elm", "policies"],
    queryFn: async () => {
      const res = await http.get<LeavePolicy[]>("/elm/policies/");
      return res.data;
    },
  });
}

export function useHolidayCalendar(year?: number) {
  return useQuery({
    queryKey: ["elm", "calendar", year],
    queryFn: async () => {
      const res = await http.get<HolidayCalendarEntry[]>("/elm/calendar/", {
        params: year ? { year } : {},
      });
      return res.data;
    },
  });
}

export function useMyLeaveApplications() {
  return useQuery({
    queryKey: ["elm", "applications", "mine"],
    queryFn: async () => {
      const res = await http.get<LeaveApplication[]>("/elm/applications/");
      return res.data;
    },
  });
}

export function usePendingApprovals() {
  return useQuery({
    queryKey: ["elm", "tasks", "approvals"],
    queryFn: async () => {
      const res = await http.get<ApprovalStep[]>("/elm/tasks/approvals/");
      return res.data;
    },
  });
}

export function usePendingSubstituteRequests() {
  return useQuery({
    queryKey: ["elm", "tasks", "substitutes"],
    queryFn: async () => {
      const res = await http.get<LeaveApplication[]>("/elm/tasks/substitutes/");
      return res.data;
    },
  });
}

export function useApplyLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ApplyLeavePayload) => {
      const res = await http.post<LeaveApplication>("/elm/applications/", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm"] });
    },
  });
}

export function useWithdrawLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (applicationId: number) => {
      const res = await http.post<LeaveApplication>(
        `/elm/applications/${applicationId}/withdraw/`
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm"] });
    },
  });
}

export function useCancelLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (applicationId: number) => {
      const res = await http.post<LeaveApplication>(
        `/elm/applications/${applicationId}/cancel/`
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm"] });
    },
  });
}

export function useExtendLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      applicationId,
      extendedEndDate,
      purpose,
    }: { applicationId: number; extendedEndDate: string; purpose: string }) => {
      const res = await http.post<LeaveApplication>(
        `/elm/applications/${applicationId}/extend/`,
        { extended_end_date: extendedEndDate, purpose }
      );
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["elm"] }),
  });
}

export function useRecordResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      applicationId,
      actualResumptionDate,
    }: { applicationId: number; actualResumptionDate: string }) => {
      const res = await http.post<LeaveApplication>(
        `/elm/applications/${applicationId}/resumption/`,
        { actual_resumption_date: actualResumptionDate }
      );
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["elm"] }),
  });
}

export function useRespondSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ applicationId, accept }: { applicationId: number; accept: boolean }) => {
      const res = await http.post<LeaveApplication>(
        `/elm/tasks/substitutes/${applicationId}/respond/`,
        { accept }
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm"] });
    },
  });
}

export function useDecideApproval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      stepId,
      decision,
      comment,
    }: {
      stepId: number;
      decision: string;
      comment?: string;
    }) => {
      const res = await http.post<ApprovalStep>(
        `/elm/tasks/approvals/${stepId}/decide/`,
        { decision, comment }
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm"] });
    },
  });
}
