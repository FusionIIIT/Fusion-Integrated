import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type { LeaveRequest, LeaveRequestInput, Page } from "./types";

const KEY = ["elm", "leave-requests"];

export function useLeaveRequests() {
  return useQuery({
    queryKey: KEY,
    queryFn: async () =>
      (await http.get<Page<LeaveRequest>>("/elm/leave-requests/")).data,
  });
}

export function useCreateLeaveRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: LeaveRequestInput) =>
      (await http.post<LeaveRequest>("/elm/leave-requests/", input)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  });
}

export function useWithdrawLeaveRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveRequest>(`/elm/leave-requests/${id}/withdraw/`)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  });
}
