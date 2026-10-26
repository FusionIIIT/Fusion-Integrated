import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  HolidayItem,
  LeaveApplication,
  LeaveBalance,
  LeaveRolloverRecord,
  LeaveType,
  Page,
} from "./types";

const ELM_KEY = "leave_elm";

export const elmKeys = {
  types: () => [ELM_KEY, "types"] as const,
  balances: () => [ELM_KEY, "balances"] as const,
  applications: () => [ELM_KEY, "applications"] as const,
  approvals: () => [ELM_KEY, "approvals"] as const,
  calendar: () => [ELM_KEY, "calendar"] as const,
};

export function useLeaveTypes() {
  return useQuery({
    queryKey: elmKeys.types(),
    queryFn: async () => (await http.get<Page<LeaveType>>("/elm/types")).data,
  });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: elmKeys.balances(),
    queryFn: async () =>
      (await http.get<Page<LeaveBalance>>("/elm/balances")).data,
  });
}

export function useLeaveApplications() {
  return useQuery({
    queryKey: elmKeys.applications(),
    queryFn: async () =>
      (await http.get<Page<LeaveApplication>>("/elm/applications")).data,
  });
}

export function useCreateLeaveApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      leave_type_code: string;
      start_date: string;
      end_date: string;
      half_day?: boolean;
      station_leave?: boolean;
      station_address?: string;
      reason?: string;
      substitute_user_id?: number | null;
    }) =>
      (await http.post<LeaveApplication>("/elm/applications", payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [ELM_KEY] });
    },
  });
}

export function useWithdrawLeaveApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveApplication>(`/elm/applications/${id}/withdraw`, {}))
        .data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [ELM_KEY] });
    },
  });
}

export function useLeaveApprovalQueue() {
  return useQuery({
    queryKey: elmKeys.approvals(),
    queryFn: async () =>
      (await http.get<Page<LeaveApplication>>("/elm/approvals")).data,
  });
}

export function useDecideLeaveApproval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      decision,
      remarks,
    }: {
      id: number;
      decision: "recommended" | "not_recommended" | "approved" | "rejected";
      remarks?: string;
    }) =>
      (
        await http.post<LeaveApplication>(`/elm/approvals/${id}/decide`, {
          decision,
          remarks: remarks ?? "",
        })
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [ELM_KEY] });
    },
  });
}

export function useRespondSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      decision,
    }: {
      id: number;
      decision: "accepted" | "declined";
    }) =>
      (
        await http.post<LeaveApplication>(`/elm/applications/${id}/substitute`, {
          decision,
        })
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [ELM_KEY] });
    },
  });
}

export function useReplaceSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      substitute_user_id,
    }: {
      id: number;
      substitute_user_id: number;
    }) =>
      (
        await http.post<LeaveApplication>(
          `/elm/applications/${id}/replace-substitute`,
          { substitute_user_id }
        )
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [ELM_KEY] });
    },
  });
}

export function useCancelLeaveApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      reason,
    }: {
      id: number;
      reason: string;
    }) =>
      (
        await http.post<LeaveApplication>(`/elm/applications/${id}/cancel`, {
          reason,
        })
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [ELM_KEY] });
    },
  });
}

export function useDecideCancellation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      decision,
      remarks,
    }: {
      id: number;
      decision: "recommended" | "not_recommended" | "approved" | "rejected";
      remarks?: string;
    }) =>
      (
        await http.post<LeaveApplication>(
          `/elm/applications/${id}/cancel/decide`,
          { decision, remarks: remarks ?? "" }
        )
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [ELM_KEY] });
    },
  });
}

export function useExtendLeaveApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      start_date,
      end_date,
      reason,
      substitute_user_id,
    }: {
      id: number;
      start_date: string;
      end_date: string;
      reason?: string;
      substitute_user_id?: number | null;
    }) =>
      (
        await http.post<LeaveApplication>(`/elm/applications/${id}/extend`, {
          start_date,
          end_date,
          reason: reason ?? "",
          substitute_user_id: substitute_user_id ?? null,
        })
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [ELM_KEY] });
    },
  });
}

export function useSubmitDutyResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      actual_resumption_date,
      remarks,
    }: {
      id: number;
      actual_resumption_date: string;
      remarks?: string;
    }) =>
      (
        await http.post<LeaveApplication>(`/elm/applications/${id}/resumption`, {
          actual_resumption_date,
          remarks: remarks ?? "",
        })
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [ELM_KEY] });
    },
  });
}

export function useReviewDutyResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      remarks,
    }: {
      id: number;
      remarks?: string;
    }) =>
      (
        await http.post<LeaveApplication>(
          `/elm/applications/${id}/resumption/decide`,
          { remarks: remarks ?? "" }
        )
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [ELM_KEY] });
    },
  });
}

export function useRecordOfflineLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      user_id: number;
      leave_type_code: string;
      start_date: string;
      end_date: string;
      sanction_reference: string;
      sanction_date: string;
      sanction_authority_name: string;
      reason?: string;
    }) =>
      (await http.post<LeaveApplication>("/elm/offline-leaves", payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [ELM_KEY] });
    },
  });
}

export function useExecuteRollover() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { target_year: number }) =>
      (await http.post<LeaveRolloverRecord[]>("/elm/rollover", payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [ELM_KEY] });
    },
  });
}

export function useHolidayCalendar() {
  return useQuery({
    queryKey: elmKeys.calendar(),
    queryFn: async () =>
      (await http.get<Page<HolidayItem>>("/elm/calendar")).data,
  });
}
