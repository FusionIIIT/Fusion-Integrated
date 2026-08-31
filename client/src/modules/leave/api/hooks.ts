/** Data access for the leave module.
 *
 *  A decision taken in one queue changes what the other queues hold, so every
 *  mutation invalidates the whole module rather than guessing which key moved.
 *  These lists are short; a stale queue that still shows a decided request is
 *  a worse failure than one extra fetch.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  ApplyPayload, AuthorityRule, Balance, Calendar, CategoryRule, Holiday,
  LeaveRequest, LedgerEntry, Policy, PolicyReadiness, SlaRule, Transition,
  VacationPeriod,
} from "./types";

const KEY = "leave";

export const keys = {
  mine: () => [KEY, "mine"] as const,
  request: (id: number) => [KEY, "request", id] as const,
  trail: (id: number) => [KEY, "trail", id] as const,
  balances: () => [KEY, "balances"] as const,
  statement: (category: string, year?: number) =>
    [KEY, "statement", category, year] as const,
  nominations: () => [KEY, "nominations"] as const,
  review: () => [KEY, "review"] as const,
  routing: () => [KEY, "routing"] as const,
  sanction: () => [KEY, "sanction"] as const,
  resumptions: () => [KEY, "resumptions"] as const,
  directory: (userId?: number) => [KEY, "directory", userId] as const,
  policies: () => [KEY, "policies"] as const,
  policyRules: (id: number) => [KEY, "policy-rules", id] as const,
  policyAuthority: (id: number) => [KEY, "policy-authority", id] as const,
  policySla: (id: number) => [KEY, "policy-sla", id] as const,
  policyReadiness: (id: number) => [KEY, "policy-readiness", id] as const,
  calendars: () => [KEY, "calendars"] as const,
  holidays: (id: number) => [KEY, "holidays", id] as const,
  vacations: (id: number) => [KEY, "vacations", id] as const,
};

function useInvalidate() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

function list<T>(key: readonly unknown[], url: string, params?: unknown) {
  return { queryKey: key, queryFn: async () =>
    (await http.get<T[]>(url, { params: params as never })).data };
}

// -- employee ------------------------------------------------------------------
export function useMyLeave() {
  return useQuery(list<LeaveRequest>(keys.mine(), "/leave/me/requests"));
}

export function useMyBalances(year?: number) {
  return useQuery({
    ...list<Balance>(keys.balances(), "/leave/me/balances", { year }),
    staleTime: 30_000,
  });
}

export function useStatement(category: string | null, year?: number) {
  return useQuery({
    queryKey: keys.statement(category ?? "", year),
    queryFn: async () => (await http.get<LedgerEntry[]>(
      `/leave/me/statement/${category}`, { params: { year } })).data,
    enabled: category != null,
  });
}

export function useTrail(id: number | null) {
  return useQuery({
    queryKey: keys.trail(id!),
    queryFn: async () =>
      (await http.get<Transition[]>(`/leave/requests/${id}/trail`)).data,
    enabled: id != null,
  });
}

export function useApply() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: ApplyPayload) =>
      (await http.post<LeaveRequest>("/leave/requests", body)).data,
    onSuccess: invalidate,
  });
}

export function useWithdraw() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async ({ id, remark }: { id: number; remark?: string }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/withdraw`, { remark }))
        .data,
    onSuccess: invalidate,
  });
}

export function useRequestCancellation() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async ({ id, remark }: { id: number; remark?: string }) =>
      (await http.post<LeaveRequest>(`/leave/requests/${id}/cancel`, { remark })).data,
    onSuccess: invalidate,
  });
}

export function useRequestExtension() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: {
      id: number; new_end: string; substitute_user_id?: number | null;
      remark?: string;
    }) => (await http.post<LeaveRequest>(
      `/leave/requests/${body.id}/extend`, body)).data,
    onSuccess: invalidate,
  });
}

export function useSubmitResumption() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: { id: number; resumed_on: string; remark?: string }) =>
      (await http.post<LeaveRequest>(
        `/leave/requests/${body.id}/resumption`, body)).data,
    onSuccess: invalidate,
  });
}

// -- substitute ----------------------------------------------------------------
export function useNominations() {
  return useQuery(list<LeaveRequest>(keys.nominations(), "/leave/nominations"));
}

export function useRespondToNomination() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: { id: number; accepted: boolean; remark?: string }) =>
      (await http.post<LeaveRequest>(
        `/leave/nominations/${body.id}/respond`, body)).data,
    onSuccess: invalidate,
  });
}

// -- the queues ----------------------------------------------------------------
export function useReviewQueue() {
  return useQuery(list<LeaveRequest>(keys.review(), "/leave/review"));
}

export function useRoutingQueue() {
  return useQuery(list<LeaveRequest>(keys.routing(), "/leave/routing"));
}

export function useSanctionQueue() {
  return useQuery(list<LeaveRequest>(keys.sanction(), "/leave/sanction"));
}

export function useResumptionQueue() {
  return useQuery(list<LeaveRequest>(keys.resumptions(), "/leave/resumptions"));
}

type Decision = { id: number; approve: boolean; remark?: string };

function decisionMutation(url: (id: number) => string) {
  return (invalidate: () => void) => ({
    mutationFn: async ({ id, ...rest }: Decision) =>
      (await http.post<LeaveRequest>(url(id), rest)).data,
    onSuccess: invalidate,
  });
}

export function useReviewDecision() {
  return useMutation(
    decisionMutation((id) => `/leave/review/${id}`)(useInvalidate()));
}

export function useSanctionDecision() {
  return useMutation(
    decisionMutation((id) => `/leave/sanction/${id}`)(useInvalidate()));
}

export function useVerifyResumption() {
  return useMutation(
    decisionMutation((id) => `/leave/resumptions/${id}/verify`)(useInvalidate()));
}

export function useRoute() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async ({ id, remark }: { id: number; remark?: string }) =>
      (await http.post<LeaveRequest>(`/leave/routing/${id}`, { remark })).data,
    onSuccess: invalidate,
  });
}

// -- administration ------------------------------------------------------------
export function useBalanceDirectory(userId: number | null, year?: number) {
  return useQuery({
    queryKey: keys.directory(userId ?? undefined),
    queryFn: async () => (await http.get<Balance[]>(
      "/leave/balances", { params: { user_id: userId, year } })).data,
    enabled: userId != null,
  });
}

export function usePolicies() {
  return useQuery(list<Policy>(keys.policies(), "/leave/admin/policies"));
}

export function usePolicyRules(id: number | null) {
  return useQuery({
    queryKey: keys.policyRules(id!),
    queryFn: async () => (await http.get<CategoryRule[]>(
      `/leave/admin/policies/${id}/rules`)).data,
    enabled: id != null,
  });
}

export function useDraftPolicy() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: {
      version: string; effective_from: string; note?: string;
      max_backdate_days?: number | null;
    }) => (await http.post<Policy>("/leave/admin/policies", body)).data,
    onSuccess: invalidate,
  });
}

export function useSetCategoryRule(policyId: number) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: Partial<CategoryRule>) =>
      (await http.post<CategoryRule>(
        `/leave/admin/policies/${policyId}/rules`, body)).data,
    onSuccess: invalidate,
  });
}

export function useAuthorityRules(id: number | null) {
  return useQuery({
    queryKey: keys.policyAuthority(id!),
    queryFn: async () => (await http.get<AuthorityRule[]>(
      `/leave/admin/policies/${id}/authority`)).data,
    enabled: id != null,
  });
}

export function useSetAuthorityRule(policyId: number) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: Partial<AuthorityRule>) =>
      (await http.post<AuthorityRule>(
        `/leave/admin/policies/${policyId}/authority`, body)).data,
    onSuccess: invalidate,
  });
}

export function useSlaRules(id: number | null) {
  return useQuery({
    queryKey: keys.policySla(id!),
    queryFn: async () =>
      (await http.get<SlaRule[]>(`/leave/admin/policies/${id}/sla`)).data,
    enabled: id != null,
  });
}

export function useSetSlaRule(policyId: number) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: Partial<SlaRule>) =>
      (await http.post<SlaRule>(`/leave/admin/policies/${policyId}/sla`, body)).data,
    onSuccess: invalidate,
  });
}

/** What still has to be added before this version can go into force. Shown
 *  beside Publish so the reason is visible before the button is pressed. */
export function usePolicyReadiness(id: number | null) {
  return useQuery({
    queryKey: keys.policyReadiness(id!),
    queryFn: async () => (await http.get<PolicyReadiness>(
      `/leave/admin/policies/${id}/readiness`)).data,
    enabled: id != null,
  });
}

export function useDraftCalendar() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: { year: number; version: string }) =>
      (await http.post<Calendar>("/leave/admin/calendars", body)).data,
    onSuccess: invalidate,
  });
}

export function useAddHoliday(calendarId: number) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: { day: string; name: string; restricted: boolean }) =>
      (await http.post<Holiday>(
        `/leave/admin/calendars/${calendarId}/holidays`, body)).data,
    onSuccess: invalidate,
  });
}

export function useAddVacation(calendarId: number) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: { name: string; starts_on: string; ends_on: string }) =>
      (await http.post<VacationPeriod>(
        `/leave/admin/calendars/${calendarId}/vacations`, body)).data,
    onSuccess: invalidate,
  });
}

export function useRenominate() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async ({ id, substitute_user_id }: {
      id: number; substitute_user_id: number;
    }) => (await http.post<LeaveRequest>(
      `/leave/requests/${id}/renominate`, { substitute_user_id })).data,
    onSuccess: invalidate,
  });
}

export function useRecordOffline() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<LeaveRequest>("/leave/admin/offline", body)).data,
    onSuccess: invalidate,
  });
}

export function usePublishPolicy() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<Policy>(`/leave/admin/policies/${id}/publish`)).data,
    onSuccess: invalidate,
  });
}

export function useCalendars() {
  return useQuery(list<Calendar>(keys.calendars(), "/leave/admin/calendars"));
}

export function useHolidays(id: number | null) {
  return useQuery({
    queryKey: keys.holidays(id!),
    queryFn: async () =>
      (await http.get<Holiday[]>(`/leave/admin/calendars/${id}/holidays`)).data,
    enabled: id != null,
  });
}

export function useVacations(id: number | null) {
  return useQuery({
    queryKey: keys.vacations(id!),
    queryFn: async () => (await http.get<VacationPeriod[]>(
      `/leave/admin/calendars/${id}/vacations`)).data,
    enabled: id != null,
  });
}

export function usePublishCalendar() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<Calendar>(`/leave/admin/calendars/${id}/publish`)).data,
    onSuccess: invalidate,
  });
}
