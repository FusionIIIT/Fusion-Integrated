/** Data access hooks for Employee Leave Management module.
 *  Uses shared http client and React Query. Every mutation invalidates
 *  relevant queries to maintain cache synchronization.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  DirectoryUser,
  LeaveApplicationPayload,
  LeaveBalance,
  LeaveCancelPayload,
  LeaveExtendPayload,
  LeaveRequest,
  LeaveResumePayload,
  LeaveReviewPayload,
  LeaveSanctionPayload,
  LeaveType,
  LeaveWithdrawPayload,
  OfflineLeaveCreatePayload,
  ResumptionRecord,
  ResumptionReviewPayload,
  SubstituteNomination,
  SubstituteResponsePayload,
} from "./types";

const KEY = "leave";

export const keys = {
  types: () => [KEY, "types"] as const,
  balances: (year?: number) => [KEY, "balances", year] as const,
  requests: (filters?: { status?: string; year?: number }) =>
    [KEY, "requests", filters] as const,
  request: (id: number) => [KEY, "request", id] as const,
  substituteNominations: () => [KEY, "substitute-nominations"] as const,
  approvals: (status?: string) => [KEY, "approvals", status] as const,
  userSearch: (q: string) => ["directory", "users", q] as const,
};

function invalidateLeave(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Queries --

export function useLeaveTypes() {
  return useQuery({
    queryKey: keys.types(),
    queryFn: async () => (await http.get<LeaveType[]>("/leave/types/")).data,
    staleTime: 60_000,
  });
}

export function useLeaveBalances(year?: number) {
  return useQuery({
    queryKey: keys.balances(year),
    queryFn: async () => {
      const params = year ? { year } : {};
      return (await http.get<LeaveBalance[]>("/leave/balances/", { params })).data;
    },
    staleTime: 30_000,
  });
}

export function useLeaveRequests(filters?: { status?: string; year?: number }) {
  return useQuery({
    queryKey: keys.requests(filters),
    queryFn: async () => {
      return (await http.get<LeaveRequest[]>("/leave/requests/", { params: filters })).data;
    },
    staleTime: 15_000,
  });
}

export function useLeaveRequest(id: number | undefined) {
  return useQuery({
    queryKey: keys.request(id!),
    queryFn: async () => {
      return (await http.get<LeaveRequest>(`/leave/requests/${id}/`)).data;
    },
    enabled: id != null && !isNaN(id),
    staleTime: 15_000,
  });
}

export function useSubstituteNominations() {
  return useQuery({
    queryKey: keys.substituteNominations(),
    queryFn: async () => {
      return (await http.get<SubstituteNomination[]>("/leave/substitute/nominations/")).data;
    },
    staleTime: 15_000,
  });
}

export function useApprovalsQueue(status?: string) {
  return useQuery({
    queryKey: keys.approvals(status),
    queryFn: async () => {
      const params = status ? { status } : {};
      return (await http.get<LeaveRequest[]>("/leave/approvals/", { params })).data;
    },
    staleTime: 15_000,
  });
}

export function useSearchDirectoryUsers(query: string) {
  return useQuery({
    queryKey: keys.userSearch(query),
    queryFn: async () => {
      if (query.trim().length < 2) return [];
      const res = await http.get<{ results: DirectoryUser[] }>("/directory/users", {
        params: { q: query.trim(), limit: 20 },
      });
      return res.data.results;
    },
    enabled: query.trim().length >= 2,
    staleTime: 30_000,
  });
}

// -- Mutations --

export function useApplyLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: LeaveApplicationPayload) => {
      return (await http.post<LeaveRequest>("/leave/applications/", payload)).data;
    },
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useWithdrawRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload?: LeaveWithdrawPayload }) => {
      return (await http.post<LeaveRequest>(`/leave/requests/${id}/withdraw/`, payload ?? {})).data;
    },
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useCancelRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: LeaveCancelPayload }) => {
      return (await http.post<LeaveRequest>(`/leave/requests/${id}/cancel/`, payload)).data;
    },
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useExtendRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: LeaveExtendPayload }) => {
      return (await http.post<LeaveRequest>(`/leave/requests/${id}/extend/`, payload)).data;
    },
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useResumeLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: LeaveResumePayload }) => {
      return (await http.post<ResumptionRecord>(`/leave/requests/${id}/resume/`, payload)).data;
    },
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useRespondSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: SubstituteResponsePayload }) => {
      return (
        await http.post<SubstituteNomination>(`/leave/substitute/nominations/${id}/respond/`, payload)
      ).data;
    },
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useReviewApproval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: LeaveReviewPayload }) => {
      return (await http.post<LeaveRequest>(`/leave/approvals/${id}/review/`, payload)).data;
    },
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useSanctionApproval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: LeaveSanctionPayload }) => {
      return (await http.post<LeaveRequest>(`/leave/approvals/${id}/sanction/`, payload)).data;
    },
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useReviewResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: ResumptionReviewPayload }) => {
      return (
        await http.post<ResumptionRecord>(`/leave/approvals/${id}/resumption/`, payload)
      ).data;
    },
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useCreateOfflineLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: OfflineLeaveCreatePayload) => {
      return (await http.post<LeaveRequest>("/leave/admin/offline/", payload)).data;
    },
    onSuccess: () => invalidateLeave(qc),
  });
}
