import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  HolidayItem,
  LeaveApplication,
  LeaveBalance,
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
      decision: "recommended" | "approved" | "rejected";
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

export function useHolidayCalendar() {
  return useQuery({
    queryKey: elmKeys.calendar(),
    queryFn: async () =>
      (await http.get<Page<HolidayItem>>("/elm/calendar")).data,
  });
}
