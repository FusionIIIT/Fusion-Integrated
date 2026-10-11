import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { elmApi } from "../api";
import type {
  ApprovalRouteInput, EmployeeProfileInput, OrganizationUnitInput,
} from "../api";
import type { CreateLeaveCaseInput, LeaveRequestInput } from "../types";

const KEY = ["elm"];

export function useElmSummary() {
  return useQuery({ queryKey: [...KEY, "summary"], queryFn: elmApi.summary });
}

export function useLeaveRequests() {
  return useQuery({ queryKey: [...KEY, "requests"], queryFn: elmApi.requests });
}

export function useLeaveInbox() {
  return useQuery({ queryKey: [...KEY, "inbox"], queryFn: elmApi.inbox });
}

export function useLeaveAccounts() {
  return useQuery({ queryKey: [...KEY, "accounts"], queryFn: elmApi.accounts });
}

export function useLeavePolicies() {
  return useQuery({ queryKey: [...KEY, "policies"], queryFn: elmApi.policies });
}

export function useLeaveCalendar() {
  return useQuery({ queryKey: [...KEY, "calendar"], queryFn: elmApi.calendar });
}

function useElmMutation<TInput, TOutput>(
  mutationFn: (input: TInput) => Promise<TOutput>,
) {
  const client = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: KEY });
    },
  });
}

export function useCreateLeave() {
  return useElmMutation((input: LeaveRequestInput) => elmApi.createRequest(input));
}

export function useLeaveAction() {
  return useElmMutation((input: { id: number; action: string; note?: string }) =>
    elmApi.action(input.id, input.action, input.note));
}

export function useWithdrawLeave() {
  return useElmMutation((id: number) => elmApi.withdraw(id));
}

export function useCreateLeaveCase() {
  return useElmMutation((input: { id: number; body: CreateLeaveCaseInput }) =>
    elmApi.createCase(input.id, input.body));
}

export function useReplaceSubstitute() {
  return useElmMutation((input: { id: number; substitute_user_id: number }) =>
    elmApi.replaceSubstitute(input.id, input.substitute_user_id));
}

export function useLeaveCaseAction() {
  return useElmMutation((input: { id: number; action: string; note?: string }) =>
    elmApi.caseAction(input.id, input.action, input.note));
}

export function useWithdrawLeaveCase() {
  return useElmMutation((id: number) => elmApi.caseWithdraw(id));
}

export function useReplaceCaseSubstitute() {
  return useElmMutation((input: { id: number; substitute_user_id: number }) =>
    elmApi.replaceCaseSubstitute(input.id, input.substitute_user_id));
}

export function useUpdateLeavePolicy() {
  return useElmMutation((input: {
    category: string;
    body: Parameters<typeof elmApi.updatePolicy>[1];
  }) => elmApi.updatePolicy(input.category, input.body));
}

export function useCreateCalendarDate() {
  return useElmMutation((input: { date: string; kind: string; label: string }) =>
    elmApi.createCalendarDate(input));
}

export function usePublishCalendarDate() {
  return useElmMutation((id: number) => elmApi.publishCalendarDate(id));
}

export function useCreateOrganizationUnit() {
  return useElmMutation((input: OrganizationUnitInput) =>
    elmApi.createOrganizationUnit(input));
}

export function useCreateEmployeeProfile() {
  return useElmMutation((input: EmployeeProfileInput) =>
    elmApi.createEmployeeProfile(input));
}

export function useCreateApprovalRoute() {
  return useElmMutation((input: ApprovalRouteInput) =>
    elmApi.createApprovalRoute(input));
}

export function useRecordOfflineLeave() {
  return useElmMutation((input: {
    user_id: number; category: string; start_date: string; end_date: string;
    half_day: string; purpose: string;
  }) => elmApi.recordOfflineLeave(input));
}

export function useAdjustLeaveAccount() {
  return useElmMutation((input: {
    user_id: number; category: string; year: number; amount: string;
    description: string;
  }) => elmApi.adjustAccount(input));
}
