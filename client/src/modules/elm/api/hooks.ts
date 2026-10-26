/** Data access for the elm module. Every mutation invalidates the keys it can affect. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type { ApplyInput, Balance, LeaveRequest } from "./types";

const KEY = "elm";

export const keys = {
  all: () => [KEY] as const,
  requests: () => [KEY, "leave-requests"] as const,
  balance: (year: number) => [KEY, "balance", year] as const,
};

export const useBalance = (year: number) =>
  useQuery({
    queryKey: keys.balance(year),
    queryFn: async () =>
      (await http.get<Balance[]>("/elm/balance/", { params: { year } })).data,
  });

export const useLeaveRequests = () =>
  useQuery({
    queryKey: keys.requests(),
    queryFn: async () => (await http.get<LeaveRequest[]>("/elm/leave-requests/")).data,
  });

export const useApplyLeaveRequest = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: ApplyInput) =>
      (await http.post<LeaveRequest>("/elm/leave-requests/", input)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.all() }),
  });
};

export const useWithdrawLeaveRequest = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<LeaveRequest>(`/elm/leave-requests/${id}/withdraw/`)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.all() }),
  });
};
