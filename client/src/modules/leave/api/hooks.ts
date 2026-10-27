import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";

const KEY = "leave";

export type LeaveCategory = "cl" | "rh";
export type LeaveHalf = "full" | "first" | "second";

export interface LeaveRequest {
  id: number;
  category: LeaveCategory;
  starts_on: string;
  ends_on: string;
  cl_half: LeaveHalf;
  reason: string;
  station_leave: boolean;
  station_leave_details: string;
  status: "pending" | "approved" | "withdrawn";
  withdrawn_at: string | null;
  created_at: string;
}

export interface CreateLeaveRequest {
  category: LeaveCategory;
  starts_on: string;
  ends_on: string;
  cl_half: LeaveHalf;
  reason: string;
  station_leave: boolean;
  station_leave_details?: string;
}

function invalidate(qc: ReturnType<typeof useQueryClient>) {
  return qc.invalidateQueries({ queryKey: [KEY] });
}

export function useLeaveRequests() {
  return useQuery({
    queryKey: [KEY, "requests"],
    queryFn: async () => (await http.get<{ results: LeaveRequest[] }>("/leave/requests")).data,
  });
}

export function useCreateLeaveRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: CreateLeaveRequest) =>
      (await http.post<LeaveRequest>("/leave/requests", body)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useWithdrawLeaveRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/withdraw`, {})).data,
    onSuccess: () => invalidate(qc),
  });
}
