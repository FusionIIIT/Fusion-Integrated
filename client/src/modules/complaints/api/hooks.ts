import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type { Announcement, Complaint, ComplaintAttachment, HandlerOption } from "./types";

const KEY = ["complaints"] as const;

export function useMyComplaints() {
  return useQuery({
    queryKey: [...KEY, "mine"],
    queryFn: async () => (await http.get<{ results: Complaint[] }>("/complaints/complaints")).data,
    staleTime: 15_000,
  });
}

export function useSubmitComplaint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { category: string; description: string; attachments?: File[] }) => {
      const headers = { "Idempotency-Key": crypto.randomUUID() };
      if (body.attachments?.length) {
        const form = new FormData();
        form.append("category", body.category);
        form.append("description", body.description);
        body.attachments.forEach((file) => form.append("attachments", file));
        return (await http.post<Complaint>("/complaints/complaints", form, { headers })).data;
      }
      return (await http.post<Complaint>("/complaints/complaints", {
        category: body.category, description: body.description,
      }, { headers })).data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: [...KEY, "mine"] }),
  });
}

export function useSubmitFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ reference, message }: { reference: string; message: string }) =>
      (await http.post(`/complaints/complaints/${reference}/feedback`, { message }, { headers: { "Idempotency-Key": crypto.randomUUID() } })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [...KEY, "mine"] }),
  });
}

export function useRequestReopening() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ reference, reason }: { reference: string; reason: string }) =>
      (await http.post(`/complaints/complaints/${reference}/reopening-requests`, { reason }, { headers: { "Idempotency-Key": crypto.randomUUID() } })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [...KEY, "mine"] }),
  });
}

export function useAnnouncements() {
  return useQuery({
    queryKey: [...KEY, "announcements"],
    queryFn: async () => (await http.get<{ results: Announcement[] }>("/complaints/announcements")).data,
    staleTime: 30_000,
  });
}

export function usePublishAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { title: string; body: string }) =>
      (await http.post<Announcement>("/complaints/announcements", body, { headers: { "Idempotency-Key": crypto.randomUUID() } })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [...KEY, "announcements"] }),
  });
}


export function useVerifyClosure() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (reference: string) =>
      (await http.post(`/complaints/complaints/${reference}/verify/user`, {})).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [...KEY, "mine"] }),
  });
}


export function useFeedbackReview() {
  return useQuery({
    queryKey: [...KEY, "feedback-review"],
    queryFn: async () => (await http.get<{ results: { id: number; complaint_reference: string; message: string; created_at: string }[] }>("/complaints/feedback")).data,
  });
}

export function useReopeningQueue() {
  return useQuery({
    queryKey: [...KEY, "reopening-queue"],
    queryFn: async () => (await http.get<{ results: { id: number; complaint_id: number; reason: string; status: string; decision_reason: string; created_at: string; decided_at: string | null }[] }>("/complaints/reopening-requests")).data,
  });
}

export function usePendingClosures() {
  return useQuery({
    queryKey: [...KEY, "closures-pending"],
    queryFn: async () => (await http.get<{ results: Complaint[] }>("/complaints/closures/pending")).data,
  });
}

export function useReviewReopening() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, decision, reason }: { id: number; decision: "approved" | "denied"; reason?: string }) =>
      (await http.post(`/complaints/reopening-requests/${id}/decision`, { decision, reason: reason ?? "" }, { headers: { "Idempotency-Key": crypto.randomUUID() } })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useVerifySupervisorClosure() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (reference: string) =>
      (await http.post(`/complaints/complaints/${reference}/verify/supervisor`, {}, { headers: { "Idempotency-Key": crypto.randomUUID() } })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useComplaintReport() {
  return useQuery({
    queryKey: [...KEY, "reports"],
    queryFn: async () => (await http.get<{ complaints_by_status: { status: string; total: number }[] }>("/complaints/reports")).data,
  });
}

export function useHandlerQueue() {
  return useQuery({
    queryKey: [...KEY, "work-queue"],
    queryFn: async () => (await http.get<{ results: Complaint[] }>("/complaints/work-queue")).data,
    staleTime: 10_000,
  });
}

export function useEscalatedQueue() {
  return useQuery({
    queryKey: [...KEY, "escalated-queue"],
    queryFn: async () => (await http.get<{ results: Complaint[] }>("/complaints/escalated")).data,
    staleTime: 15_000,
  });
}

export function useAssignmentQueue() {
  return useQuery({
    queryKey: [...KEY, "assignment-queue"],
    queryFn: async () => (await http.get<{ results: Complaint[] }>("/complaints/assignment-queue")).data,
    staleTime: 10_000,
  });
}

export function useHandlerOptions() {
  return useQuery({
    queryKey: [...KEY, "handlers"],
    queryFn: async () => (await http.get<HandlerOption[]>("/complaints/handlers")).data,
    staleTime: 60_000,
  });
}

export function useAssignComplaint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { reference: string; assignee_user_id: number; category: string; priority: "low" | "medium" | "high" }) =>
      (await http.post<Complaint>(`/complaints/complaints/${input.reference}/assign`, {
        assignee_user_id: input.assignee_user_id, category: input.category, priority: input.priority,
      })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useHandlerAction(action: "progress" | "resolve" | "reject" | "escalate") {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { reference: string; text: string }) => {
      const body = action === "progress" ? { details: input.text }
        : action === "resolve" ? { details: input.text } : { reason: input.text };
      return (await http.post(`/complaints/complaints/${input.reference}/${action}`, body)).data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useComplaintAttachments(reference: string) {
  return useQuery({
    queryKey: [...KEY, "attachments", reference],
    queryFn: async () => (await http.get<{ results: ComplaintAttachment[] }>(
      `/complaints/complaints/${reference}/attachments`,
    )).data,
  });
}

export function useUploadComplaintAttachment(reference: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return (await http.post<ComplaintAttachment>(
        `/complaints/complaints/${reference}/attachments`, body,
      )).data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: [...KEY, "attachments", reference] }),
  });
}
