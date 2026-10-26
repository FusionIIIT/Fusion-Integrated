/** TanStack Query hooks for the Leave (ELM) module. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  CreateLeavePayload,
  HolidayItem,
  LeaveApplication,
  LeaveBalance,
  VacationItem,
} from "./types";

const KEY = "leave";

export const keys = {
  applications: (filters?: Record<string, unknown>) => [KEY, "applications", filters] as const,
  application: (id: number) => [KEY, "application", id] as const,
  balances: (year?: number) => [KEY, "balances", year] as const,
  substituteTasks: () => [KEY, "substitute-tasks"] as const,
  approvals: () => [KEY, "approvals"] as const,
  holidays: (year?: number) => [KEY, "holidays", year] as const,
  vacations: (year?: number) => [KEY, "vacations", year] as const,
};

export function useApplications(filters?: { status?: string; leave_type?: string }) {
  return useQuery({
    queryKey: keys.applications(filters),
    queryFn: async () => {
      const res = await http.get<{ results: LeaveApplication[] }>("/leave/applications", {
        params: filters,
      });
      return res.data.results;
    },
  });
}

export function useApplication(id: number | null) {
  return useQuery({
    queryKey: keys.application(id ?? 0),
    queryFn: async () => {
      if (!id) return null;
      const res = await http.get<LeaveApplication>(`/leave/applications/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useBalances(year?: number) {
  return useQuery({
    queryKey: keys.balances(year),
    queryFn: async () => {
      const res = await http.get<{ results: LeaveBalance[] }>("/leave/balances", {
        params: year ? { year } : {},
      });
      return res.data.results;
    },
  });
}

export function useSubstituteTasks() {
  return useQuery({
    queryKey: keys.substituteTasks(),
    queryFn: async () => {
      const res = await http.get<{ results: LeaveApplication[] }>("/leave/substitute/pending");
      return res.data.results;
    },
  });
}

export function useApprovals() {
  return useQuery({
    queryKey: keys.approvals(),
    queryFn: async () => {
      const res = await http.get<{ results: LeaveApplication[] }>("/leave/approvals/pending");
      return res.data.results;
    },
  });
}

export function useHolidays(year?: number) {
  return useQuery({
    queryKey: keys.holidays(year),
    queryFn: async () => {
      const res = await http.get<{ results: HolidayItem[] }>("/leave/calendar/holidays", {
        params: year ? { year } : {},
      });
      return res.data.results;
    },
  });
}

export function useVacations(year?: number) {
  return useQuery({
    queryKey: keys.vacations(year),
    queryFn: async () => {
      const res = await http.get<{ results: VacationItem[] }>("/leave/calendar/vacations", {
        params: year ? { year } : {},
      });
      return res.data.results;
    },
  });
}

// Mutations

export function useSubmitApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateLeavePayload) => {
      const res = await http.post<LeaveApplication>("/leave/applications", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useWithdrawApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await http.post<LeaveApplication>(`/leave/applications/${id}/withdraw`);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useCancelApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason: string }) => {
      const res = await http.post<LeaveApplication>(`/leave/applications/${id}/cancel`, { reason });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useExtendApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      new_end_date,
      reason,
      substitute_user_id,
    }: {
      id: number;
      new_end_date: string;
      reason: string;
      substitute_user_id?: number | null;
    }) => {
      const res = await http.post<LeaveApplication>(`/leave/applications/${id}/extend`, {
        new_end_date,
        reason,
        substitute_user_id,
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useResumptionSubmit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      actual_resumption_date,
      remarks,
    }: {
      id: number;
      actual_resumption_date: string;
      remarks?: string;
    }) => {
      const res = await http.post<LeaveApplication>(`/leave/applications/${id}/resumption`, {
        actual_resumption_date,
        remarks,
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useRespondSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      accept,
      remarks,
    }: {
      id: number;
      accept: boolean;
      remarks?: string;
    }) => {
      const res = await http.post<LeaveApplication>(`/leave/substitute/${id}/respond`, {
        accept,
        remarks,
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useReplaceSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, new_substitute_id }: { id: number; new_substitute_id: number }) => {
      const res = await http.post<LeaveApplication>(`/leave/substitute/${id}/replace`, {
        new_substitute_id,
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useUnitHeadReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      decision,
      remarks,
    }: {
      id: number;
      decision: string;
      remarks?: string;
    }) => {
      const res = await http.post<LeaveApplication>(`/leave/approvals/${id}/unit-head`, {
        decision,
        remarks,
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useEstablishmentRoute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remarks }: { id: number; remarks?: string }) => {
      const res = await http.post<LeaveApplication>(`/leave/approvals/${id}/establishment`, {
        remarks,
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useSanctionDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      decision,
      remarks,
    }: {
      id: number;
      decision: string;
      remarks?: string;
    }) => {
      const res = await http.post<LeaveApplication>(`/leave/approvals/${id}/sanction`, {
        decision,
        remarks,
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useReviewCancellation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      decision,
      remarks,
    }: {
      id: number;
      decision: string;
      remarks?: string;
    }) => {
      const res = await http.post<LeaveApplication>(`/leave/applications/${id}/cancellation-review`, {
        decision,
        remarks,
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useReviewResumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remarks }: { id: number; remarks?: string }) => {
      const res = await http.post<LeaveApplication>(`/leave/applications/${id}/resumption-review`, {
        remarks,
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useTriggerYearEnd() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (year?: number) => {
      const res = await http.post("/leave/admin/yearend", year ? { year } : {});
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useTriggerSLA() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await http.post("/leave/admin/sla");
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useAdjustBalance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      user_id: number;
      year: number;
      leave_type: string;
      delta: number;
      is_credit: boolean;
    }) => {
      const res = await http.post("/leave/balances/adjust", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useRecordOffline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      applicant_user_id: number;
      applicant_kind: string;
      leave_type: string;
      start_date: string;
      end_date: string;
      reason: string;
      sanction_ref: string;
      sanction_date: string;
      sanctioned_by: string;
      half_day_type?: string;
    }) => {
      const res = await http.post("/leave/offline/record", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}
