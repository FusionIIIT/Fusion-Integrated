import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type { LeaveRequest, LeaveRequestInput, Page } from "./types";

const ROOT = "/elm/requests";
const key = ["elm", "requests"] as const;

export function useLeaveRequests(filters?: {
  status?: string;
  leave_type?: string;
  from_date?: string;
  to_date?: string;
}) {
  return useQuery({
    queryKey: [...key, filters],
    queryFn: async () =>
      (await http.get<Page<LeaveRequest>>(`${ROOT}/history/`, { params: filters }))
        .data,
    staleTime: 15_000,
  });
}

export function useLeaveRequest(id: number | undefined) {
  return useQuery({
    queryKey: [...key, id],
    queryFn: async () => (await http.get<LeaveRequest>(`${ROOT}/${id}/`)).data,
    enabled: id != null,
  });
}

export function useSubmitLeaveRequest() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: LeaveRequestInput) =>
      (await http.post<LeaveRequest>(`${ROOT}/`, body)).data,
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
}

export function useWithdrawLeaveRequest() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveRequest>(`${ROOT}/${id}/withdraw/`, {})).data,
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
}
