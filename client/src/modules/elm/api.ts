import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../lib/http";
import type {
  LeaveApplication,
  LeaveApproval,
  LeaveBalance,
  LeaveType,
} from "./types";

interface PaginatedResponse<T> {
  results: T[];
  next?: string | null;
  previous?: string | null;
}

export function useLeaveApplications() {
  return useQuery({
    queryKey: ["elm", "applications"],
    queryFn: async () => {
      const res = await http.get<PaginatedResponse<LeaveApplication> | LeaveApplication[]>("/elm/applications/");
      return Array.isArray(res.data) ? res.data : res.data.results ?? [];
    },
  });
}

export function useLeaveTypes() {
  return useQuery({
    queryKey: ["elm", "types"],
    queryFn: async () => {
      const res = await http.get<PaginatedResponse<LeaveType> | LeaveType[]>("/elm/types/");
      return Array.isArray(res.data) ? res.data : res.data.results ?? [];
    },
  });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: ["elm", "balances"],
    queryFn: async () => {
      const res = await http.get<PaginatedResponse<LeaveBalance> | LeaveBalance[]>("/elm/balances/");
      return Array.isArray(res.data) ? res.data : res.data.results ?? [];
    },
  });
}

export function useLeaveApprovals() {
  return useQuery({
    queryKey: ["elm", "approvals"],
    queryFn: async () => {
      const res = await http.get<PaginatedResponse<LeaveApproval> | LeaveApproval[]>("/elm/approvals/");
      return Array.isArray(res.data) ? res.data : res.data.results ?? [];
    },
  });
}

export function useSubmitLeaveApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      leave_type: number;
      start_date: string;
      end_date: string;
      reason: string;
    }) => {
      const res = await http.post<LeaveApplication>("/elm/applications/", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm", "applications"] });
      qc.invalidateQueries({ queryKey: ["elm", "balances"] });
    },
  });
}

export function useWithdrawLeaveApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await http.patch<LeaveApplication>(`/elm/applications/${id}/withdraw/`);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm", "applications"] });
      qc.invalidateQueries({ queryKey: ["elm", "balances"] });
    },
  });
}
