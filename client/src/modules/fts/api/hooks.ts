/** Data access hooks for the File Tracking System (FTS).
 *
 *  Mutations invalidate the fts query cache so UI state updates reliably.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  CreateFilePayload,
  FileAuditLog,
  FileDetail,
  FileListItem,
  FileMovement,
  ForwardFilePayload,
  ReturnFilePayload,
  UpdateDraftPayload,
  UsageMetrics,
} from "./types";

const KEY = "fts";

export const keys = {
  inbox: () => [KEY, "inbox"] as const,
  outbox: () => [KEY, "outbox"] as const,
  drafts: () => [KEY, "drafts"] as const,
  detail: (id: number | null) => [KEY, "file", id] as const,
  history: (id: number | null) => [KEY, "history", id] as const,
  usage: () => [KEY, "governance", "usage"] as const,
  auditLogs: (fileId?: number | null) => [KEY, "governance", "audit", fileId] as const,
};

function invalidateFts(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

export function useInboxFiles() {
  return useQuery({
    queryKey: keys.inbox(),
    queryFn: async () => {
      const res = await http.get<FileListItem[]>("/fts/inbox/");
      return res.data;
    },
    staleTime: 15_000,
  });
}

export function useOutboxFiles() {
  return useQuery({
    queryKey: keys.outbox(),
    queryFn: async () => {
      const res = await http.get<FileListItem[]>("/fts/outbox/");
      return res.data;
    },
    staleTime: 15_000,
  });
}

export function useDraftFiles() {
  return useQuery({
    queryKey: keys.drafts(),
    queryFn: async () => {
      const res = await http.get<FileListItem[]>("/fts/drafts/");
      return res.data;
    },
    staleTime: 15_000,
  });
}

export function useFileDetail(id: number | null) {
  return useQuery({
    queryKey: keys.detail(id),
    queryFn: async () => {
      if (!id) return null;
      const res = await http.get<FileDetail>(`/fts/files/${id}/`);
      return res.data;
    },
    enabled: !!id,
    staleTime: 15_000,
  });
}

export function useFileHistory(id: number | null) {
  return useQuery({
    queryKey: keys.history(id),
    queryFn: async () => {
      if (!id) return [];
      const res = await http.get<FileMovement[]>(`/fts/files/${id}/history/`);
      return res.data;
    },
    enabled: !!id,
    staleTime: 15_000,
  });
}

export function useGovernanceUsage() {
  return useQuery({
    queryKey: keys.usage(),
    queryFn: async () => {
      const res = await http.get<UsageMetrics>("/fts/governance/usage/");
      return res.data;
    },
    staleTime: 30_000,
  });
}

export function useGovernanceAuditLogs(fileId?: number | null) {
  return useQuery({
    queryKey: keys.auditLogs(fileId),
    queryFn: async () => {
      const res = await http.get<FileAuditLog[]>("/fts/governance/audit-logs/", {
        params: fileId ? { file_id: fileId } : undefined,
      });
      return res.data;
    },
    staleTime: 15_000,
  });
}

export function useCreateFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateFilePayload) => {
      const res = await http.post<FileDetail>("/fts/files/", payload);
      return res.data;
    },
    onSuccess: () => invalidateFts(qc),
  });
}

export function useUpdateDraft(fileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UpdateDraftPayload) => {
      const res = await http.put<FileDetail>(`/fts/files/${fileId}/`, payload);
      return res.data;
    },
    onSuccess: () => invalidateFts(qc),
  });
}

export function useForwardFile(fileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ForwardFilePayload) => {
      const res = await http.post<FileMovement>(`/fts/files/${fileId}/forward/`, payload);
      return res.data;
    },
    onSuccess: () => invalidateFts(qc),
  });
}

export function useReturnFile(fileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ReturnFilePayload) => {
      const res = await http.post<FileMovement>(`/fts/files/${fileId}/return/`, payload);
      return res.data;
    },
    onSuccess: () => invalidateFts(qc),
  });
}

export function useArchiveFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (fileId: number) => {
      const res = await http.post<FileDetail>(`/fts/files/${fileId}/archive/`);
      return res.data;
    },
    onSuccess: () => invalidateFts(qc),
  });
}

export function useDiscardDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (fileId: number) => {
      await http.post<void>(`/fts/files/${fileId}/discard/`);
    },
    onSuccess: () => invalidateFts(qc),
  });
}
