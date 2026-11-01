/** Data access for the patent module. Writes invalidate the whole module key. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../lib/http";

const KEY = "patents";

export interface AppRow {
  id: number;
  application_no: string;
  applicant_user_id: number;
  title: string;
  status: string;
  status_label: string;
  director_user_id: number | null;
  attorney_user_id: number | null;
  attorney_status: string;
  budget_status: string;
  budget_total: string | null;
  review_due_on: string | null;
}

export interface AppDetail extends AppRow {
  abstract: string;
  description: string;
  claims: string;
  decision_justification: string;
  revision_count: number;
  opinion: { recommendation: string; text: string };
  filing: { external_filing_id: string; filing_date: string | null };
  events: {
    id: number; action: string; from_state: string; to_state: string;
    detail: string; created_at: string;
  }[];
}

export function useApplications() {
  return useQuery({
    queryKey: [KEY, "list"],
    queryFn: async () =>
      (await http.get<{ results: AppRow[] }>("/patents/applications")).data.results,
  });
}

export function useApplication(id: number) {
  return useQuery({
    queryKey: [KEY, "one", id],
    queryFn: async () => (await http.get<AppDetail>(`/patents/applications/${id}`)).data,
  });
}

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<AppDetail>("/patents/applications", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}

export function useAppAction(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ action, body = {} }: {
      action: string; body?: Record<string, unknown>;
    }) => (await http.post<AppDetail>(`/patents/applications/${id}/${action}`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}

export interface Notice {
  id: number;
  kind: string;
  message: string;
  created_at: string;
  read: boolean;
  application_id: number | null;
}

export function useNotices() {
  return useQuery({
    queryKey: [KEY, "notices"],
    queryFn: async () =>
      (await http.get<{ results: Notice[] }>("/patents/notifications")).data.results,
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (nid: number) => (await http.post(`/patents/notifications/${nid}/read`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}

export interface Summary {
  total: number;
  by_status: Record<string, number>;
  approved_budget: string;
}

export function useSummary() {
  return useQuery({
    queryKey: [KEY, "summary"],
    queryFn: async () => (await http.get<Summary>("/patents/reports/summary")).data,
  });
}
