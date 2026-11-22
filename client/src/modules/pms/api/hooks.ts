import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  InternalReview,
  MaintenanceRenewal,
  OfficeAction,
  PatentApplication,
  PatentFinancialTransaction,
} from "../types";

const KEY = "pms";

export const pmsKeys = {
  applications: (f?: unknown) => [KEY, "applications", f] as const,
  application: (id: number) => [KEY, "application", id] as const,
  transactions: (id: number) => [KEY, "transactions", id] as const,
  reports: () => [KEY, "reports"] as const,
};

export function useApplications(filters?: { status?: string; search?: string }) {
  return useQuery({
    queryKey: pmsKeys.applications(filters),
    queryFn: () => http.get<PatentApplication[]>("/api/v1/pms/applications/", { params: filters }),
  });
}

export function useApplication(id: number) {
  return useQuery({
    queryKey: pmsKeys.application(id),
    queryFn: () => http.get<PatentApplication>(`/api/v1/pms/applications/${id}/`),
    enabled: id > 0,
  });
}

export function useApplicationTransactions(appId: number) {
  return useQuery({
    queryKey: pmsKeys.transactions(appId),
    queryFn: () => http.get<PatentFinancialTransaction[]>(`/api/v1/pms/applications/${appId}/transactions/`),
    enabled: appId > 0,
  });
}

export function usePmsReportSummary() {
  return useQuery({
    queryKey: pmsKeys.reports(),
    queryFn: () => http.get<Record<string, unknown>>("/api/v1/pms/reports/summary/"),
  });
}

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<PatentApplication>) =>
      http.post<PatentApplication>("/api/v1/pms/applications/", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "applications"] });
    },
  });
}

export function useSubmitApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      http.post<PatentApplication>(`/api/v1/pms/applications/${id}/submit/`, {}),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: pmsKeys.application(id) });
      qc.invalidateQueries({ queryKey: [KEY, "applications"] });
    },
  });
}

export function useWithdrawApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      http.post<PatentApplication>(`/api/v1/pms/applications/${id}/withdraw/`, { reason }),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: pmsKeys.application(id) });
      qc.invalidateQueries({ queryKey: [KEY, "applications"] });
    },
  });
}

export function useSubmitReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      http.post<InternalReview>(`/api/v1/pms/applications/${id}/review/`, payload),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: pmsKeys.application(id) });
      qc.invalidateQueries({ queryKey: [KEY, "applications"] });
    },
  });
}

export function useAssignDirector() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, directorId }: { id: number; directorId: number }) =>
      http.post<PatentApplication>(`/api/v1/pms/applications/${id}/assign-director/`, { director_id: directorId }),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: pmsKeys.application(id) });
      qc.invalidateQueries({ queryKey: [KEY, "applications"] });
    },
  });
}
