import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type { LeaveRequest, LeaveAccount } from "./types";
const base = "/elm";
export function useMyLeave() {
  return useQuery({ queryKey: ["elm", "mine"], queryFn: async () => (await http.get<LeaveRequest[]>(`${base}/mine`)).data });
}
export function useLeaveAccounts() {
  return useQuery({ queryKey: ["elm", "accounts"], queryFn: async () => (await http.get<LeaveAccount[]>(`${base}/accounts`)).data });
}
export function useApplyLeave() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async (payload: Record<string, unknown>) => (await http.post<LeaveRequest>(`${base}/apply`, payload)).data, onSuccess: () => qc.invalidateQueries({ queryKey: ["elm"] }) });
}
export function useLeaveAction() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async ({ id, action, reason }: { id: number; action: string; reason?: string }) => (await http.post<LeaveRequest>(`${base}/requests/${id}/action`, { action, reason })).data, onSuccess: () => qc.invalidateQueries({ queryKey: ["elm"] }) });
}
