import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  FileAuditLog,
  FileMovement,
  TrackedFileDetail,
  TrackedFileSummary,
} from "./types";

const KEY = "filetracking";

export const keys = {
  inbox: () => [KEY, "inbox"] as const,
  outbox: () => [KEY, "outbox"] as const,
  drafts: () => [KEY, "drafts"] as const,
  archived: () => [KEY, "archived"] as const,
  detail: (id: number) => [KEY, "detail", id] as const,
  history: (id: number) => [KEY, "history", id] as const,
  audit: (fileId?: number) => [KEY, "audit", fileId] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

export function useInboxFiles() {
  return useQuery({
    queryKey: keys.inbox(),
    queryFn: async () =>
      (await http.get<TrackedFileSummary[]>("/api/v1/filetracking/files/inbox/")).data,
  });
}

export function useOutboxFiles() {
  return useQuery({
    queryKey: keys.outbox(),
    queryFn: async () =>
      (await http.get<TrackedFileSummary[]>("/api/v1/filetracking/files/outbox/")).data,
  });
}

export function useDraftFiles() {
  return useQuery({
    queryKey: keys.drafts(),
    queryFn: async () =>
      (await http.get<TrackedFileSummary[]>("/api/v1/filetracking/files/drafts/")).data,
  });
}

export function useArchivedFiles() {
  return useQuery({
    queryKey: keys.archived(),
    queryFn: async () =>
      (await http.get<TrackedFileSummary[]>("/api/v1/filetracking/files/archived/")).data,
  });
}

export function useFileDetail(id: number) {
  return useQuery({
    queryKey: keys.detail(id),
    queryFn: async () =>
      (await http.get<TrackedFileDetail>(`/api/v1/filetracking/files/${id}/`)).data,
    enabled: id > 0,
  });
}

export function useFileHistory(id: number) {
  return useQuery({
    queryKey: keys.history(id),
    queryFn: async () =>
      (await http.get<FileMovement[]>(`/api/v1/filetracking/files/${id}/history/`)).data,
    enabled: id > 0,
  });
}

export function useCreateFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      subject: string;
      initial_comment: string;
      is_draft?: boolean;
      recipient_user_id?: number | null;
      recipient_designation?: string;
    }) =>
      (await http.post<TrackedFileDetail>("/api/v1/filetracking/files/", data)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useForwardFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      fileId,
      recipientUserId,
      recipientDesignation,
      comment,
    }: {
      fileId: number;
      recipientUserId: number;
      recipientDesignation?: string;
      comment: string;
    }) =>
      (
        await http.post<FileMovement>(`/api/v1/filetracking/files/${fileId}/forward/`, {
          recipient_user_id: recipientUserId,
          recipient_designation: recipientDesignation || "",
          comment,
        })
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReturnFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ fileId, comment }: { fileId: number; comment: string }) =>
      (
        await http.post<FileMovement>(`/api/v1/filetracking/files/${fileId}/return/`, {
          comment,
        })
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useArchiveFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ fileId, comment }: { fileId: number; comment?: string }) =>
      (
        await http.post<TrackedFileDetail>(`/api/v1/filetracking/files/${fileId}/archive/`, {
          comment: comment || "",
        })
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAuditLogs(fileId?: number) {
  return useQuery({
    queryKey: keys.audit(fileId),
    queryFn: async () => {
      const q = fileId ? `?file_id=${fileId}` : "";
      return (await http.get<FileAuditLog[]>(`/api/v1/filetracking/governance/audit/${q}`)).data;
    },
  });
}
