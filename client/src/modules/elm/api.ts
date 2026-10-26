import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../lib/http";

export interface LeaveType {
  id: number;
  code: string;
  name: string;
  max_days_per_year: number;
  requires_document: boolean;
  is_active: boolean;
}

export interface LeaveBalance {
  id: number;
  leave_type: number;
  year: number;
  allotted: number;
  used: number;
  available: number;
}

export interface LeaveApplication {
  id: number;
  employee_id: number;
  leave_type: number;
  start_date: string;
  end_date: string;
  days: number;
  reason: string;
  status: string;
  approver_id: number | null;
  remarks: string;
  decided_at: string | null;
  created_at: string;
}

const KEY = "elm";

export const useLeaveTypes = () =>
  useQuery<LeaveType[]>({
    queryKey: [KEY, "types"],
    queryFn: async () => (await http.get<LeaveType[]>("/elm/types")).data,
    staleTime: 15_000,
  });

export const useMyApplications = () =>
  useQuery<LeaveApplication[]>({
    queryKey: [KEY, "applications"],
    queryFn: async () => (await http.get<LeaveApplication[]>("/elm/applications")).data,
    staleTime: 15_000,
  });

export const usePendingApprovals = () =>
  useQuery<LeaveApplication[]>({
    queryKey: [KEY, "applications", "pending"],
    queryFn: async () => (await http.get<LeaveApplication[]>("/elm/applications/pending")).data,
    staleTime: 15_000,
  });

export const useMyBalance = (year?: number) =>
  useQuery<LeaveBalance[]>({
    queryKey: [KEY, "balance", year],
    queryFn: async () => (await http.get<LeaveBalance[]>("/elm/balance", { params: { year } })).data,
    staleTime: 15_000,
  });

export const useApplyLeave = () =>
  useMutation<LeaveApplication, Error, { leave_type: number; start_date: string; end_date: string; reason: string }>({
    mutationFn: async (body) => (await http.post<LeaveApplication>("/elm/applications", body)).data,
    onSuccess: () => {
      const qc = useQueryClient();
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });

export const useDecide = () =>
  useMutation<LeaveApplication, Error, { id: number; approve: boolean; remarks?: string }>({
    mutationFn: async (vars) => (await http.post<LeaveApplication>(`/elm/applications/${vars.id}/decide`, { approve: vars.approve, remarks: vars.remarks })).data,
    onSuccess: () => {
      const qc = useQueryClient();
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });

export const useWithdraw = () =>
  useMutation<LeaveApplication, Error, { id: number }>({
    mutationFn: async (vars) => (await http.post<LeaveApplication>(`/elm/applications/${vars.id}/withdraw`, {})).data,
    onSuccess: () => {
      const qc = useQueryClient();
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });

export const useCancelLeave = () =>
  useMutation<LeaveApplication, Error, { id: number }>({
    mutationFn: async (vars) => (await http.post<LeaveApplication>(`/elm/applications/${vars.id}/cancel`, {})).data,
    onSuccess: () => {
      const qc = useQueryClient();
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });

export const useCreateLeaveType = () =>
  useMutation<LeaveType, Error, { code: string; name: string; max_days_per_year: number; requires_document?: boolean }>({
    mutationFn: async (body) => (await http.post<LeaveType>("/elm/admin/types", body)).data,
    onSuccess: () => {
      const qc = useQueryClient();
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });

export const useAllotBalance = () =>
  useMutation<LeaveBalance, Error, { employee_id: number; leave_type_id: number; year: number; allotted: number }>({
    mutationFn: async (body) => (await http.post<LeaveBalance>("/elm/admin/balances", body)).data,
    onSuccess: () => {
      const qc = useQueryClient();
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
