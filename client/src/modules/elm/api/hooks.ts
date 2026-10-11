import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type { Holiday, LeaveApplication, LeaveBalance, LeaveCategory, Page } from "./types";

const KEY = "employee-leave";
const invalidate = (qc: ReturnType<typeof useQueryClient>) => qc.invalidateQueries({ queryKey: [KEY] });

export function useLeaveCategories() { return useQuery({ queryKey: [KEY, "categories"], queryFn: async () => (await http.get<Page<LeaveCategory>>("/leave/categories")).data, staleTime: 60_000 }); }
export function useLeaveBalances() { return useQuery({ queryKey: [KEY, "balances"], queryFn: async () => (await http.get<Page<LeaveBalance>>("/leave/balances")).data }); }
export function useLeaveApplications() { return useQuery({ queryKey: [KEY, "applications"], queryFn: async () => (await http.get<Page<LeaveApplication>>("/leave/applications")).data }); }
export function useLeaveHolidays() { return useQuery({ queryKey: [KEY, "calendar"], queryFn: async () => (await http.get<Page<Holiday>>("/leave/calendar")).data }); }
export function useCreateLeaveApplication() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async (body: Record<string, unknown>) => (await http.post<LeaveApplication>("/leave/applications", body)).data, onSuccess: () => invalidate(qc) });
}
export function useWithdrawLeave() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async (id: number) => (await http.post<LeaveApplication>(`/leave/applications/${id}/withdraw`, {})).data, onSuccess: () => invalidate(qc) });
}
