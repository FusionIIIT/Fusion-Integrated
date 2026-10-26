/** TanStack Query hooks for the leave module. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  HolidayCalendar,
  LeaveApplication,
  LeaveApplicationCreatePayload,
  LeaveBalance,
  LeaveCancellationRequestPayload,
  LeaveCancellationReviewPayload,
  LeaveReplacementSubstitutePayload,
  LeaveResumptionReviewPayload,
  LeaveResumptionSubmitPayload,
  LeaveReviewActionPayload,
  LeaveSubstituteResponsePayload,
  LeaveType,
  LeaveWithdrawPayload,
} from "./types";

const KEY = "leave";

export const keys = {
  types: () => [KEY, "types"] as const,
  calendar: (year?: number) => [KEY, "calendar", year] as const,
  balances: (year?: number) => [KEY, "balances", year] as const,
  applications: (params?: Record<string, string | undefined>) =>
    [KEY, "applications", params] as const,
  application: (id: number) => [KEY, "application", id] as const,
};

function invalidateLeave(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

export function useLeaveTypes() {
  return useQuery({
    queryKey: keys.types(),
    queryFn: async () => (await http.get<LeaveType[]>("/leave/types/")).data,
    staleTime: 60_000,
  });
}

export function useHolidayCalendar(year?: number) {
  return useQuery({
    queryKey: keys.calendar(year),
    queryFn: async () =>
      (await http.get<HolidayCalendar[]>("/leave/calendar/", { params: { year } })).data,
    staleTime: 60_000,
  });
}

export function useLeaveBalances(year?: number) {
  return useQuery({
    queryKey: keys.balances(year),
    queryFn: async () =>
      (await http.get<LeaveBalance[]>("/leave/balances/", { params: { year } })).data,
    staleTime: 30_000,
  });
}

export function useLeaveApplications(params?: Record<string, string | undefined>) {
  return useQuery({
    queryKey: keys.applications(params),
    queryFn: async () =>
      (await http.get<LeaveApplication[]>("/leave/applications/", { params })).data,
    staleTime: 15_000,
  });
}

export function useLeaveApplication(id: number | null) {
  return useQuery({
    queryKey: keys.application(id ?? 0),
    queryFn: async () =>
      (await http.get<LeaveApplication>(`/leave/applications/${id}/`)).data,
    enabled: Boolean(id),
  });
}

export function useSubmitLeaveApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: LeaveApplicationCreatePayload) =>
      (await http.post<LeaveApplication>("/leave/applications/", payload)).data,
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useRespondToSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: LeaveSubstituteResponsePayload & { id: number }) =>
      (
        await http.post<LeaveApplication>(
          `/leave/applications/${id}/substitute/`,
          payload
        )
      ).data,
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useNominateReplacementSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: LeaveReplacementSubstitutePayload & { id: number }) =>
      (
        await http.post<LeaveApplication>(
          `/leave/applications/${id}/replacement-substitute/`,
          payload
        )
      ).data,
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useReviewLeaveApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: LeaveReviewActionPayload & { id: number }) =>
      (await http.post<LeaveApplication>(`/leave/applications/${id}/review/`, payload)).data,
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useWithdrawLeaveApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: LeaveWithdrawPayload & { id: number }) =>
      (
        await http.post<LeaveApplication>(
          `/leave/applications/${id}/withdraw/`,
          payload
        )
      ).data,
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useCancelLeaveApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: LeaveCancellationRequestPayload & { id: number }) =>
      (await http.post<LeaveApplication>(`/leave/applications/${id}/cancel/`, payload)).data,
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useReviewCancellation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: LeaveCancellationReviewPayload & { id: number }) =>
      (
        await http.post<LeaveApplication>(
          `/leave/applications/${id}/cancellation-review/`,
          payload
        )
      ).data,
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useSubmitResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: LeaveResumptionSubmitPayload & { id: number }) =>
      (
        await http.post<LeaveApplication>(
          `/leave/applications/${id}/resumption/`,
          payload
        )
      ).data,
    onSuccess: () => invalidateLeave(qc),
  });
}

export function useReviewResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: LeaveResumptionReviewPayload & { id: number }) =>
      (
        await http.post<LeaveApplication>(
          `/leave/applications/${id}/resumption-review/`,
          payload
        )
      ).data,
    onSuccess: () => invalidateLeave(qc),
  });
}
