/** Data access for ELM. Every mutation invalidates the whole module key. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { saveBlob } from "../../../lib/download";
import { http } from "../../../lib/http";
import type {
  Balance, CalendarEntry, CalendarVersion, Employee, LeaveDetail, LeaveInput,
  LeaveRequest, Notification, OfflineInput, OfflineRecord, Page, PolicyVersion,
} from "./types";

const KEY = "elm";

export const keys = {
  mine: () => [KEY, "mine"] as const,
  detail: (id: number) => [KEY, "detail", id] as const,
  balances: () => [KEY, "balances"] as const,
  account: (uid: number) => [KEY, "account", uid] as const,
  substitutions: () => [KEY, "substitutions"] as const,
  queue: () => [KEY, "queue"] as const,
  resumptions: () => [KEY, "resumptions"] as const,
  policies: () => [KEY, "policies"] as const,
  calendars: () => [KEY, "calendars"] as const,
  offline: () => [KEY, "offline"] as const,
  employees: (q: string) => [KEY, "employees", q] as const,
  notifications: () => [KEY, "notifications"] as const,
};

function useInvalidate() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

function list<T>(key: readonly unknown[], url: string) {
  return {
    queryKey: key,
    queryFn: async () => (await http.get<Page<T>>(url)).data,
  };
}

export const useMyRequests = () => useQuery(list<LeaveRequest>(keys.mine(), "/elm/requests"));
export const useSubstitutions = () =>
  useQuery(list<LeaveRequest>(keys.substitutions(), "/elm/substitutions"));
export const useQueue = () => useQuery(list<LeaveRequest>(keys.queue(), "/elm/queue"));
export const useResumptions = () =>
  useQuery(list<LeaveRequest>(keys.resumptions(), "/elm/resumptions"));
export const usePolicies = () =>
  useQuery(list<PolicyVersion>(keys.policies(), "/elm/admin/policies"));
export const useCalendars = () =>
  useQuery(list<CalendarVersion>(keys.calendars(), "/elm/admin/calendars"));
export const useOfflineRecords = () =>
  useQuery(list<OfflineRecord>(keys.offline(), "/elm/admin/offline"));
export const useNotifications = () =>
  useQuery(list<Notification>(keys.notifications(), "/elm/notifications"));

export function useRequest(id: number | null) {
  return useQuery({
    queryKey: keys.detail(id ?? 0),
    queryFn: async () => (await http.get<LeaveDetail>(`/elm/requests/${id}`)).data,
    enabled: id != null,
  });
}

export function useBalances() {
  return useQuery({
    queryKey: keys.balances(),
    queryFn: async () => (await http.get<Balance>("/elm/balances")).data,
  });
}

export function useAccount(userId: number | null) {
  return useQuery({
    queryKey: keys.account(userId ?? 0),
    queryFn: async () =>
      (await http.get<Balance>("/elm/admin/accounts", { params: { user_id: userId } })).data,
    enabled: userId != null,
    retry: false,
  });
}

export function useEmployeeSearch(q: string) {
  return useQuery({
    queryKey: keys.employees(q),
    queryFn: async () =>
      (await http.get<{ results: Employee[] }>("/elm/employees", { params: { q } }))
        .data.results,
    enabled: q.trim().length >= 2,
    staleTime: 60_000,
  });
}

function usePost<V>(url: (v: V) => string, body: (v: V) => unknown = (v) => v) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (v: V) => (await http.post(url(v), body(v))).data,
    onSuccess: invalidate,
  });
}

export const useApply = () =>
  usePost<LeaveInput>(() => "/elm/requests");
export const useModify = () =>
  usePost<{ id: number; data: LeaveInput }>((v) => `/elm/requests/${v.id}/modify`,
    (v) => v.data);
export const useWithdraw = () =>
  usePost<{ id: number; reason: string }>((v) => `/elm/requests/${v.id}/withdraw`,
    (v) => ({ reason: v.reason }));
export const useCancel = () =>
  usePost<{ id: number; reason: string }>((v) => `/elm/requests/${v.id}/cancel`,
    (v) => ({ reason: v.reason }));
export const useRenominate = () =>
  usePost<{ id: number; substitute_user_id: number; responsibility: string }>(
    (v) => `/elm/requests/${v.id}/substitute`,
    (v) => ({ substitute_user_id: v.substitute_user_id, responsibility: v.responsibility }));
export const useExtend = () =>
  usePost<{ id: number; end_date: string; purpose: string;
    substitute_user_id: number | null }>(
    (v) => `/elm/requests/${v.id}/extend`,
    (v) => ({ end_date: v.end_date, purpose: v.purpose,
      substitute_user_id: v.substitute_user_id }));
export const useResume = () =>
  usePost<{ id: number; actual_return_date: string; note: string }>(
    (v) => `/elm/requests/${v.id}/resume`,
    (v) => ({ actual_return_date: v.actual_return_date, note: v.note }));
export const useRespondSubstitution = () =>
  usePost<{ id: number; accept: boolean; note: string }>(
    (v) => `/elm/substitutions/${v.id}/respond`,
    (v) => ({ accept: v.accept, note: v.note }));
export const useDecide = () =>
  usePost<{ id: number; event: string; note: string }>(
    (v) => `/elm/queue/${v.id}/decide`, (v) => ({ event: v.event, note: v.note }));
export const useVerify = () =>
  usePost<{ id: number; verified: boolean; note: string }>(
    (v) => `/elm/resumptions/${v.id}/verify`,
    (v) => ({ verified: v.verified, note: v.note }));
export const useCreatePolicy = () =>
  usePost<Omit<PolicyVersion, "id" | "status" | "published_at" | "created_at">>(
    () => "/elm/admin/policies");
export const usePublishPolicy = () =>
  usePost<number>((id) => `/elm/admin/policies/${id}/publish`, () => ({}));
export const useCreateCalendar = () =>
  usePost<{ name: string; effective_from: string; entries: CalendarEntry[] }>(
    () => "/elm/admin/calendars");
export const usePublishCalendar = () =>
  usePost<number>((id) => `/elm/admin/calendars/${id}/publish`, () => ({}));
export const useRecordOffline = () =>
  usePost<OfflineInput>(() => "/elm/admin/offline");

/** EL-UC-013: fetched, not navigated to, so a refusal stays in the app. */
export function usePrint() {
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await http.get(`/elm/requests/${id}/print`, { responseType: "blob" });
      saveBlob(res.data as Blob, `leave-${id}.txt`);
    },
  });
}
