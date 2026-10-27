import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  LeaveApplyPayload,
  LeaveBalance,
  LeaveRequest,
  LeaveTransitionPayload,
  SubstituteActionPayload,
} from "./types";

const KEY = "leave";

export const leaveKeys = {
  all: [KEY] as const,
  requests: () => [KEY, "requests"] as const,
  request: (id: number) => [KEY, "request", id] as const,
  balances: () => [KEY, "balances"] as const,
};

export function useLeaveRequests() {
  return useQuery({
    queryKey: leaveKeys.requests(),
    queryFn: async () => {
      const resp = await http.get<LeaveRequest[]>("/api/v1/leave/requests/");
      return resp.data;
    },
  });
}

export function useLeaveRequest(id: number) {
  return useQuery({
    queryKey: leaveKeys.request(id),
    queryFn: async () => {
      const resp = await http.get<LeaveRequest>(`/api/v1/leave/requests/${id}/`);
      return resp.data;
    },
    enabled: Boolean(id),
  });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: leaveKeys.balances(),
    queryFn: async () => {
      const resp = await http.get<LeaveBalance[]>("/api/v1/leave/balances/");
      return resp.data;
    },
  });
}

export function useApplyLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: LeaveApplyPayload) => {
      const resp = await http.post<LeaveRequest>(
        "/api/v1/leave/requests/apply/",
        payload
      );
      return resp.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: leaveKeys.all });
    },
  });
}

export function useSubstituteAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: SubstituteActionPayload & { id: number }) => {
      const resp = await http.post<LeaveRequest>(
        `/api/v1/leave/requests/${id}/substitute-action/`,
        payload
      );
      return resp.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: leaveKeys.all });
    },
  });
}

export function useTransitionLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: LeaveTransitionPayload & { id: number }) => {
      const resp = await http.post<LeaveRequest>(
        `/api/v1/leave/requests/${id}/transition/`,
        payload
      );
      return resp.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: leaveKeys.all });
    },
  });
}
