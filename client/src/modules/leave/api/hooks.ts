import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Calendar,
  LeaveBalance,
  LeaveRequest,
  LeaveTransition,
  LedgerEntry,
  Policy,
} from "./types";

const KEY = "leave";

export const keys = {
  myRequests: () => [KEY, "me", "requests"] as const,
  myBalances: () => [KEY, "me", "balances"] as const,
  statement: (cat: string) => [KEY, "me", "statement", cat] as const,
  request: (id: number) => [KEY, "request", id] as const,
  trail: (id: number) => [KEY, "trail", id] as const,
  nominations: () => [KEY, "nominations"] as const,
  reviewQueue: () => [KEY, "review"] as const,
  routingQueue: () => [KEY, "routing"] as const,
  sanctionQueue: () => [KEY, "sanction"] as const,
  resumptionsQueue: () => [KEY, "resumptions"] as const,
  balances: (userId?: number) => [KEY, "balances", userId] as const,
  policies: () => [KEY, "admin", "policies"] as const,
  calendars: () => [KEY, "admin", "calendars"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

export function useMyRequests() {
  return useQuery({
    queryKey: keys.myRequests(),
    queryFn: async () => (await http.get<LeaveRequest[]>("/leave/me/requests")).data,
  });
}

export function useMyBalances() {
  return useQuery({
    queryKey: keys.myBalances(),
    queryFn: async () => (await http.get<LeaveBalance[]>("/leave/me/balances")).data,
  });
}

export function useStatement(category: string) {
  return useQuery({
    queryKey: keys.statement(category),
    queryFn: async () => (await http.get<LedgerEntry[]>(`/leave/me/statement/${category}`)).data,
    enabled: Boolean(category),
  });
}

export function useLeaveDetail(id: number | undefined) {
  return useQuery({
    queryKey: keys.request(id ?? 0),
    queryFn: async () => (await http.get<LeaveRequest>(`/leave/requests/${id}`)).data,
    enabled: Boolean(id),
  });
}

export function useLeaveTrail(id: number | undefined) {
  return useQuery({
    queryKey: keys.trail(id ?? 0),
    queryFn: async () => (await http.get<LeaveTransition[]>(`/leave/requests/${id}/trail`)).data,
    enabled: Boolean(id),
  });
}

export function useApplyLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      category: string;
      starts_on: string;
      ends_on: string;
      reason: string;
      half?: string;
      evidence_reference?: string;
      substitute_user_id?: number | null;
      station?: { destination: string; emergency_contact: string };
    }) => (await http.post<LeaveRequest>("/leave/requests", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdrawLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remark }: { id: number; remark: string }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/withdraw`, { remark })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCancelLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remark }: { id: number; remark: string }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/cancel`, { remark })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useExtendLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      new_end,
      substitute_user_id,
      remark,
    }: {
      id: number;
      new_end: string;
      substitute_user_id?: number | null;
      remark: string;
    }) =>
      (
        await http.post<LeaveRequest>(`/leave/requests/${id}/extend`, {
          new_end,
          substitute_user_id,
          remark,
        })
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRenominate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, substitute_user_id }: { id: number; substitute_user_id: number }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/renominate`, { substitute_user_id })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, resumed_on, remark }: { id: number; resumed_on: string; remark: string }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/resumption`, { resumed_on, remark })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useNominations() {
  return useQuery({
    queryKey: keys.nominations(),
    queryFn: async () => (await http.get<LeaveRequest[]>("/leave/nominations")).data,
  });
}

export function useRespondNomination() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, accepted, remark }: { id: number; accepted: boolean; remark: string }) =>
      (await http.post<LeaveRequest>(`/leave/nominations/${id}/respond`, { accepted, remark })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReviewQueue() {
  return useQuery({
    queryKey: keys.reviewQueue(),
    queryFn: async () => (await http.get<LeaveRequest[]>("/leave/review")).data,
  });
}

export function useReviewDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, approve, remark }: { id: number; approve: boolean; remark: string }) =>
      (await http.post<LeaveRequest>(`/leave/review/${id}`, { approve, remark })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRoutingQueue() {
  return useQuery({
    queryKey: keys.routingQueue(),
    queryFn: async () => (await http.get<LeaveRequest[]>("/leave/routing")).data,
  });
}

export function useRoutingDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remark }: { id: number; remark: string }) =>
      (await http.post<LeaveRequest>(`/leave/routing/${id}`, { remark })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSanctionQueue() {
  return useQuery({
    queryKey: keys.sanctionQueue(),
    queryFn: async () => (await http.get<LeaveRequest[]>("/leave/sanction")).data,
  });
}

export function useSanctionDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, approve, remark }: { id: number; approve: boolean; remark: string }) =>
      (await http.post<LeaveRequest>(`/leave/sanction/${id}`, { approve, remark })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useResumptionsQueue() {
  return useQuery({
    queryKey: keys.resumptionsQueue(),
    queryFn: async () => (await http.get<LeaveRequest[]>("/leave/resumptions")).data,
  });
}

export function useVerifyResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remark }: { id: number; remark: string }) =>
      (await http.post<LeaveRequest>(`/leave/resumptions/${id}/verify`, { remark })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useBalances(userId?: number) {
  return useQuery({
    queryKey: keys.balances(userId),
    queryFn: async () =>
      (await http.get<LeaveBalance[]>("/leave/balances", { params: userId ? { user_id: userId } : {} })).data,
  });
}

export function usePolicies() {
  return useQuery({
    queryKey: keys.policies(),
    queryFn: async () => (await http.get<Policy[]>("/leave/admin/policies")).data,
  });
}

export function useCalendars() {
  return useQuery({
    queryKey: keys.calendars(),
    queryFn: async () => (await http.get<Calendar[]>("/leave/admin/calendars")).data,
  });
}
