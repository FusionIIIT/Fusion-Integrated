/** Data access for ELM. Every mutation invalidates the whole module's cache:
 *  an approval changes both the queue and the applicant's balance. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  LeaveApplication, LeaveBalance, LeaveRequest, LeaveStatus, Page,
} from "./types";

const KEY = "elm";

export function useMyLeave() {
  return useQuery({
    queryKey: [KEY, "mine"],
    queryFn: async () =>
      (await http.get<Page<LeaveRequest>>("/elm/requests", { params: { mine: 1 } })).data,
  });
}

/** Requests still waiting on someone other than the applicant. */
export function useApprovalQueue() {
  return useQuery({
    queryKey: [KEY, "queue"],
    queryFn: async () =>
      (await http.get<Page<LeaveRequest>>("/elm/requests", {
        params: { status: "pending,recommended,not_recommended" },
      })).data,
  });
}

export function useBalances(year?: number) {
  return useQuery({
    queryKey: [KEY, "balances", year],
    queryFn: async () =>
      (await http.get<LeaveBalance[]>("/elm/balances", { params: { year } })).data,
  });
}

export function useApply() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: LeaveApplication) =>
      (await http.post<LeaveRequest>("/elm/requests/apply", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}

export function useLeaveTransition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, to_status, remarks }: {
      id: number; to_status: LeaveStatus; remarks?: string;
    }) =>
      (await http.post<LeaveRequest>(`/elm/requests/${id}/transition`,
        { to_status, remarks: remarks ?? "" })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}
