import { useMutation, useQuery, type UseMutationOptions } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type { LeaveType, LeaveBalance, LeaveApplication } from "./types";

const KEY = "elm";

export const keys = {
  leaveTypes: () => [KEY, "leave-types"] as const,
  leaveBalances: () => [KEY, "balances"] as const,
  leaveApplications: () => [KEY, "applications"] as const,
};

export function useLeaveTypes() {
  return useQuery({
    queryKey: keys.leaveTypes(),
    queryFn: async () => (await http.get<LeaveType[]>("/elm/leave-types")).data,
    staleTime: 30_000,
  });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: keys.leaveBalances(),
    queryFn: async () => (await http.get<LeaveBalance[]>("/elm/balances")).data,
    staleTime: 30_000,
  });
}

export function useLeaveApplications() {
  return useQuery({
    queryKey: keys.leaveApplications(),
    queryFn: async () => (await http.get<LeaveApplication[]>("/elm/applications")).data,
    staleTime: 15_000,
  });
}

export function useCreateLeaveApplication(options?: UseMutationOptions<LeaveApplication, unknown, Partial<LeaveApplication>>) {
  return useMutation({
    mutationFn: async (body: Partial<LeaveApplication>) => (await http.post<LeaveApplication>("/elm/applications/create", body)).data,
    ...options,
  });
}

export function useWithdrawLeaveApplication(id: number, options?: UseMutationOptions<void, unknown, void>) {
  return useMutation({
    mutationFn: async () => (await http.post(`/elm/applications/${id}/withdraw`, {})).data,
    ...options,
  });
}
