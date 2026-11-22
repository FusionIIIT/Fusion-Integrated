import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  CmsAnnouncement, CmsComplaint, CmsFeedback, CmsPage, CmsReopeningRequest,
  CmsReport, CmsRoleAssignment, CmsConfig,
} from "./types";

const ROOT = "/cms";
const KEY = ["cms"] as const;

export function useCmsConfig(enabled = true) {
  return useQuery({
    queryKey: [...KEY, "config"],
    queryFn: async () => (await http.get<CmsConfig>(`${ROOT}/config`)).data,
    enabled,
  });
}

function useCmsMutation<TBody, TResult>(path: string, method: "post" | "patch" = "post") {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id?: number; body: TBody }) => {
      const url = `${ROOT}${path.replace(":id", String(id ?? ""))}`;
      const response = method === "patch"
        ? await http.patch<TResult>(url, body) : await http.post<TResult>(url, body);
      return response.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useCmsComplaints(filters: Record<string, string> = {}, mine = false,
                                enabled = true) {
  return useQuery({
    queryKey: [...KEY, "complaints", mine, filters],
    queryFn: async () => (await http.get<CmsPage<CmsComplaint>>(
      mine ? `${ROOT}/complaints/mine` : `${ROOT}/complaints`,
      { params: { limit: 100, ...filters } })).data,
    staleTime: 10_000,
    enabled,
  });
}

export function useCmsEscalations(filters: Record<string, string> = {}) {
  return useQuery({
    queryKey: [...KEY, "escalations", filters],
    queryFn: async () => (await http.get<CmsPage<CmsComplaint>>(
      `${ROOT}/escalations`, { params: { limit: 100, ...filters } })).data,
  });
}

export function useCmsReopeningRequests() {
  return useQuery({
    queryKey: [...KEY, "reopening"],
    queryFn: async () => (await http.get<CmsPage<CmsReopeningRequest>>(
      `${ROOT}/reopening-requests`, { params: { limit: 100 } })).data,
  });
}

export function useCmsFeedback() {
  return useQuery({
    queryKey: [...KEY, "feedback"],
    queryFn: async () => (await http.get<CmsPage<CmsFeedback>>(
      `${ROOT}/feedback`, { params: { limit: 100 } })).data,
  });
}

export function useCmsAnnouncements() {
  return useQuery({
    queryKey: [...KEY, "announcements"],
    queryFn: async () => (await http.get<CmsPage<CmsAnnouncement>>(
      `${ROOT}/announcements`, { params: { limit: 100 } })).data,
  });
}

export function useCmsReports(enabled = true) {
  return useQuery({
    queryKey: [...KEY, "reports"],
    queryFn: async () => (await http.get<CmsReport>(`${ROOT}/reports`)).data,
    enabled,
  });
}

export function useCmsRoles() {
  return useQuery({
    queryKey: [...KEY, "roles"],
    queryFn: async () => (await http.get<CmsRoleAssignment[]>(`${ROOT}/roles`)).data,
  });
}

export function useSubmitComplaint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { category: string; description: string; attachments: File[] }) => {
      const form = new FormData();
      form.append("category", body.category);
      form.append("description", body.description);
      body.attachments.forEach((file) => form.append("attachments", file));
      return (await http.post<CmsComplaint>(`${ROOT}/complaints`, form)).data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export const useHandlingSetup = () => useCmsMutation<
  { category: string; priority: string; note: string }, CmsComplaint
>("/complaints/:id/handling");
export const useAddProgress = () => useCmsMutation<{ text: string }, unknown>(
  "/complaints/:id/progress");
export const useComplaintOutcome = () => useCmsMutation<
  { outcome: "resolved" | "rejected"; details: string }, CmsComplaint
>("/complaints/:id/outcome");
export const useUserClosure = () => useCmsMutation<Record<string, never>, CmsComplaint>(
  "/complaints/:id/closure/user");
export const useSupervisorClosure = () => useCmsMutation<Record<string, never>, CmsComplaint>(
  "/complaints/:id/closure/supervisor");
export const useReopenComplaint = () => useCmsMutation<{ text: string }, CmsReopeningRequest>(
  "/complaints/:id/reopening");
export const useReopeningDecision = () => useCmsMutation<
  { decision: "approved" | "denied"; note: string }, CmsReopeningRequest
>("/reopening-requests/:id/decision");
export const useEscalateComplaint = () => useCmsMutation<Record<string, never>, CmsComplaint>(
  "/complaints/:id/escalation");
export const useSubmitFeedback = () => useCmsMutation<{ text: string }, CmsFeedback>(
  "/complaints/:id/feedback");
export const usePublishCmsAnnouncement = () => useCmsMutation<
  { title: string; body: string; notify_users: boolean }, CmsAnnouncement
>("/announcements");
export const useAssignCmsRole = () => useCmsMutation<
  { role: "handler" | "supervisor"; user_id: number; starts_at: string; ends_at: string },
  CmsRoleAssignment
>("/roles");
