/** React Query data-access hooks for the ELM module. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type { LeaveType, LeaveRequest, LeaveBalance, SubstituteResponse, LeaveStatus } from "./types";

const KEY = "elm";

export const keys = {
  types: () => [KEY, "types"] as const,
  requests: () => [KEY, "requests"] as const,
  balances: () => [KEY, "balances"] as const,
  substitutes: () => [KEY, "substitutes"] as const,
};

export function useLeaveTypes() {
  return useQuery({
    queryKey: keys.types(),
    queryFn: async () => (await http.get<LeaveType[]>("/elm/types")).data,
    staleTime: 60_000,
  });
}

export function useLeaveRequests() {
  return useQuery({
    queryKey: keys.requests(),
    queryFn: async () => (await http.get<LeaveRequest[]>("/elm/requests")).data,
    staleTime: 15_000,
  });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: keys.balances(),
    queryFn: async () => (await http.get<LeaveBalance[]>("/elm/balances")).data,
    staleTime: 30_000,
  });
}

export function useSubstituteResponses() {
  return useQuery({
    queryKey: keys.substitutes(),
    queryFn: async () => (await http.get<SubstituteResponse[]>("/elm/substitute-responses")).data,
    staleTime: 15_000,
  });
}

export function useApplyLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      leave_type_id: number;
      start_date: string;
      end_date: string;
      reason: string;
      half_day_type?: string;
      is_station_leave?: boolean;
    }) => {
      const resp = await http.post<{ id: number; status: string }>("/elm/requests", payload);
      return resp.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useTransitionLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, target_status, reason }: { id: number; target_status: LeaveStatus; reason?: string }) => {
      const resp = await http.post<{ id: number; status: string }>(`/elm/requests/${id}/transition`, {
        target_status,
        reason,
      });
      return resp.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useRespondSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      status,
      remarks,
    }: {
      id: number;
      status: "ACCEPTED" | "DECLINED";
      remarks?: string;
    }) => {
      const resp = await http.post<{ id: number; status: string; request_status: string }>(
        `/elm/substitute-responses/${id}/respond`,
        { status, remarks }
      );
      return resp.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

