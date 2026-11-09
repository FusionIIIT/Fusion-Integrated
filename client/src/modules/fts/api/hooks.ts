import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  ArchiveInput, ArchiveResult, CreateDraftInput, CreateDraftResult,
  DraftSummary, FileDetail, FileSummary, ForwardInput, HistoryMovement,
  MovementResult, ReturnInput,
} from "./types";

const BASE = "/fts/files";

export const keys = {
  all: ["fts"] as const,
  inbox: () => ["fts", "inbox"] as const,
  outbox: () => ["fts", "outbox"] as const,
  drafts: () => ["fts", "drafts"] as const,
  file: (id: number) => ["fts", "file", id] as const,
  history: (id: number) => ["fts", "file", id, "history"] as const,
};

export function useInbox() {
  return useQuery({
    queryKey: keys.inbox(),
    queryFn: async () => (await http.get<FileSummary[]>(`${BASE}/inbox/`)).data,
  });
}

export function useOutbox() {
  return useQuery({
    queryKey: keys.outbox(),
    queryFn: async () => (await http.get<FileSummary[]>(`${BASE}/outbox/`)).data,
  });
}

export function useDrafts() {
  return useQuery({
    queryKey: keys.drafts(),
    queryFn: async () => (await http.get<DraftSummary[]>(`${BASE}/drafts/`)).data,
  });
}

export function useFile(id: number) {
  return useQuery({
    queryKey: keys.file(id),
    queryFn: async () => (await http.get<FileDetail>(`${BASE}/${id}/`)).data,
    enabled: Number.isFinite(id),
  });
}

export function useFileHistory(id: number) {
  return useQuery({
    queryKey: keys.history(id),
    queryFn: async () =>
      (await http.get<HistoryMovement[]>(`${BASE}/${id}/history/`)).data,
    enabled: Number.isFinite(id),
  });
}

/** Every write can change inbox, outbox, drafts and one file at once, so they
 *  all refetch rather than patching caches by hand. */
function useInvalidateFts() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: keys.all });
}

export function useCreateDraft() {
  const invalidate = useInvalidateFts();
  return useMutation({
    mutationFn: async (input: CreateDraftInput) =>
      (await http.post<CreateDraftResult>(`${BASE}/create-draft/`, input)).data,
    onSuccess: invalidate,
  });
}

export function useForwardFile(id: number) {
  const invalidate = useInvalidateFts();
  return useMutation({
    mutationFn: async (input: ForwardInput) =>
      (await http.post<MovementResult>(`${BASE}/${id}/forward/`, input)).data,
    onSuccess: invalidate,
  });
}

export function useReturnFile(id: number) {
  const invalidate = useInvalidateFts();
  return useMutation({
    mutationFn: async (input: ReturnInput) =>
      (await http.post<MovementResult>(
        `${BASE}/${id}/return_file_action/`, input)).data,
    onSuccess: invalidate,
  });
}

export function useArchiveFile(id: number) {
  const invalidate = useInvalidateFts();
  return useMutation({
    mutationFn: async (input: ArchiveInput) =>
      (await http.post<ArchiveResult>(`${BASE}/${id}/archive/`, input)).data,
    onSuccess: invalidate,
  });
}
