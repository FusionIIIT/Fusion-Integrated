/** Data access hooks for SPACS module. */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type { Application, AwardCandidate, AwardCycle, Scheme } from "./types";

const KEY = "spacs";

export const keys = {
  schemes: () => [KEY, "schemes"] as const,
  scheme: (id: number) => [KEY, "scheme", id] as const,
  cycles: () => [KEY, "cycles"] as const,
  applications: () => [KEY, "applications"] as const,
  application: (id: number) => [KEY, "application", id] as const,
  verifications: () => [KEY, "verifications"] as const,
  awards: () => [KEY, "awards"] as const,
  tasks: () => [KEY, "tasks"] as const,
};

export function useSchemes() {
  return useQuery({
    queryKey: keys.schemes(),
    queryFn: async () => (await http.get<Scheme[]>("/api/v1/spacs/schemes")).data,
  });
}

export function useCycles() {
  return useQuery({
    queryKey: keys.cycles(),
    queryFn: async () => (await http.get<AwardCycle[]>("/api/v1/spacs/cycles")).data,
  });
}

export function useApplications() {
  return useQuery({
    queryKey: keys.applications(),
    queryFn: async () => (await http.get<Application[]>("/api/v1/spacs/applications")).data,
  });
}

export function useVerificationQueue() {
  return useQuery({
    queryKey: keys.verifications(),
    queryFn: async () => (await http.get<Application[]>("/api/v1/spacs/verifications")).data,
  });
}

export function useAwards() {
  return useQuery({
    queryKey: keys.awards(),
    queryFn: async () => (await http.get<AwardCandidate[]>("/api/v1/spacs/awards")).data,
  });
}

export function useSubmitApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      scheme_code: string;
      academic_cycle: string;
      cpi: number;
      family_income?: number;
    }) => (await http.post<Application>("/api/v1/spacs/applications", data)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.applications() });
    },
  });
}

export function useVerifyApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, notes }: { id: number; action: "verify" | "defect"; notes?: string }) =>
      (await http.post<Application>(`/api/v1/spacs/verifications/${id}/action`, { action, notes })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.verifications() });
      qc.invalidateQueries({ queryKey: keys.applications() });
    },
  });
}

export function useRecordDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { application_id: string; outcome: "approved" | "rejected"; reason?: string }) =>
      (await http.post<Application>("/api/v1/spacs/decisions/action", data)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.applications() });
    },
  });
}
