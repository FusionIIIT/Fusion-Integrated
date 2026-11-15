/** React Query hooks for Complaint Management System (CMS). */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  ActiveCmsRoles,
  AssignComplaintPayload,
  AssignRolePayload,
  CmsRoleAssignment,
  ComplaintAnnouncement,
  ComplaintCategory,
  ComplaintDetail,
  ComplaintListItem,
  ManualEscalatePayload,
  PublishAnnouncementPayload,
  RejectComplaintPayload,
  ReopeningRequestPayload,
  ReopeningReviewPayload,
  ReportsSummary,
  ResolveComplaintPayload,
  SlaCheckResult,
  SubmitComplaintPayload,
  SubmitFeedbackPayload,
  UpdateProgressPayload,
  VerifyClosePayload,
} from "./types";

const KEY = "complaints";

export const keys = {
  all: [KEY] as const,
  list: (filters?: Record<string, unknown>) => [KEY, "list", filters] as const,
  detail: (id: number | string) => [KEY, "detail", id] as const,
  categories: () => [KEY, "categories"] as const,
  announcements: (categoryId?: number | null) => [KEY, "announcements", categoryId] as const,
  reportsSummary: () => [KEY, "reports", "summary"] as const,
  roles: () => [KEY, "roles"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// Queries
export function useComplaints(filters?: {
  status?: string;
  priority?: string;
  category_id?: number | string;
  is_escalated?: boolean | string;
  search?: string;
}) {
  return useQuery({
    queryKey: keys.list(filters),
    queryFn: async () => {
      const res = await http.get<ComplaintListItem[]>("/complaints/", { params: filters });
      return res.data;
    },
  });
}

export function useComplaint(id: number | string | undefined) {
  return useQuery({
    queryKey: keys.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error("Complaint ID is required");
      const res = await http.get<ComplaintDetail>(`/complaints/${id}/`);
      return res.data;
    },
    enabled: Boolean(id),
  });
}

export function useCategories() {
  return useQuery({
    queryKey: keys.categories(),
    queryFn: async () => {
      const res = await http.get<ComplaintCategory[]>("/complaints/categories/");
      return res.data;
    },
  });
}

export function useAnnouncements(categoryId?: number | null) {
  return useQuery({
    queryKey: keys.announcements(categoryId),
    queryFn: async () => {
      const res = await http.get<ComplaintAnnouncement[]>("/complaints/announcements/", {
        params: categoryId ? { category_id: categoryId } : undefined,
      });
      return res.data;
    },
  });
}

export function useReportsSummary() {
  return useQuery({
    queryKey: keys.reportsSummary(),
    queryFn: async () => {
      const res = await http.get<ReportsSummary>("/complaints/reports/summary/");
      return res.data;
    },
  });
}

export function useCmsRoles() {
  return useQuery({
    queryKey: keys.roles(),
    queryFn: async () => {
      const res = await http.get<ActiveCmsRoles>("/complaints/roles/");
      return res.data;
    },
  });
}

// Mutations
export function useSubmitComplaint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SubmitComplaintPayload) => {
      const form = new FormData();
      form.append("category_id", String(payload.category_id));
      form.append("location", payload.location);
      form.append("description", payload.description);
      if (payload.priority) form.append("priority", payload.priority);
      if (payload.verification_required) form.append("verification_required", payload.verification_required);
      if (payload.attachments) {
        for (const file of payload.attachments) {
          form.append("attachments", file);
        }
      }
      const res = await http.post<ComplaintDetail>("/complaints/", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAssignComplaint(id: number | string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AssignComplaintPayload) => {
      const res = await http.post<ComplaintDetail>(`/complaints/${id}/assign/`, payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateProgress(id: number | string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UpdateProgressPayload) => {
      const res = await http.post<ComplaintDetail>(`/complaints/${id}/progress/`, payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useResolveComplaint(id: number | string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ResolveComplaintPayload) => {
      const res = await http.post<ComplaintDetail>(`/complaints/${id}/resolve/`, payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRejectComplaint(id: number | string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: RejectComplaintPayload) => {
      const res = await http.post<ComplaintDetail>(`/complaints/${id}/reject/`, payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useVerifyCloseComplaint(id?: number | string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args?: { id?: number | string; remarks?: string } | VerifyClosePayload) => {
      const targetId = args && "id" in args && args.id ? args.id : id;
      const payload: VerifyClosePayload = args && "remarks" in args ? { remarks: args.remarks } : {};
      const res = await http.post<ComplaintDetail>(`/complaints/${targetId}/verify-close/`, payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReopenRequest(id: number | string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ReopeningRequestPayload) => {
      const res = await http.post<ComplaintDetail>(`/complaints/${id}/reopen-request/`, payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReopenReview(id: number | string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ReopeningReviewPayload) => {
      const res = await http.post<ComplaintDetail>(`/complaints/${id}/reopen-review/`, payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useManualEscalate(id: number | string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ManualEscalatePayload) => {
      const res = await http.post<ComplaintDetail>(`/complaints/${id}/escalate/`, payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitFeedback(id: number | string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SubmitFeedbackPayload) => {
      const res = await http.post(`/complaints/${id}/feedback/`, payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublishAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: PublishAnnouncementPayload) => {
      const res = await http.post<ComplaintAnnouncement>("/complaints/announcements/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAssignCmsRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AssignRolePayload) => {
      const res = await http.post<CmsRoleAssignment>("/complaints/roles/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useTriggerSlaCheck() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await http.post<SlaCheckResult>("/complaints/sla-check/");
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}
