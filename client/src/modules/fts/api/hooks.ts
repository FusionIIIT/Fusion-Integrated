import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type { FileSummary, FileDetail, HistoryEvent, Recipient, CreateFileInput, UpdateFileInput, ForwardInput } from "./types";

export function useInbox() {
  return useQuery({ queryKey: ["fts", "inbox"], queryFn: async () => (await http.get<FileSummary[]>("/fts/inbox/")).data });
}

export function useOutbox() {
  return useQuery({ queryKey: ["fts", "outbox"], queryFn: async () => (await http.get<FileSummary[]>("/fts/outbox/")).data });
}

export function useDrafts() {
  return useQuery({ queryKey: ["fts", "drafts"], queryFn: async () => (await http.get<FileSummary[]>("/fts/drafts/")).data });
}

export function useFile(id: number) {
  return useQuery({ queryKey: ["fts", "file", id], queryFn: async () => (await http.get<FileDetail>(`/fts/files/${id}/`)).data, enabled: Number.isFinite(id) });
}

export function useFileHistory(id: number) {
  return useQuery({ queryKey: ["fts", "file", id, "history"], queryFn: async () => (await http.get<HistoryEvent[]>(`/fts/files/${id}/history/`)).data, enabled: Number.isFinite(id) });
}

export function useRecipients() {
  return useQuery({ queryKey: ["fts", "recipients"], queryFn: async () => (await http.get<Recipient[]>("/fts/recipients/")).data });
}

export function useCreateFile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateFileInput) =>
      (await http.post<FileDetail>("/fts/files/", input)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["fts"] }),
  });
}

export function useUpdateFile(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: UpdateFileInput) =>
      (await http.patch<FileDetail>(`/fts/files/${id}/`, input)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["fts"] }),
  });
}

export function useDiscardDraft(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await http.delete(`/fts/files/${id}/`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["fts"] }),
  });
}

export function useForwardFile(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: ForwardInput) =>
      (await http.post<FileDetail>(`/fts/files/${id}/forward/`, input)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["fts"] }),
  });
}

export function useReturnFile(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { comment: string }) =>
      (await http.post<FileDetail>(`/fts/files/${id}/return/`, input)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["fts"] }),
  });
}

export function useArchiveFile(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      (await http.post<FileDetail>(`/fts/files/${id}/archive/`, {})).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["fts"] }),
  });
}

export function errorMessage(e: unknown): string {
  const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  return detail ?? "Something went wrong";
}
