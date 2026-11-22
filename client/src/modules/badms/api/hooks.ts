import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type { ArchiveRequest, BackupRun, Page } from "./types";

const KEY = "badms";

export function useBackupRuns() {
  return useQuery({
    queryKey: [KEY, "backup-runs"],
    queryFn: async () => (await http.get<Page<BackupRun>>("/badms/backup_runs")).data,
  });
}

export function useRunManualBackup() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async () => (await http.post<BackupRun>("/badms/backup_runs", {})).data,
    onSuccess: () => client.invalidateQueries({ queryKey: [KEY] }),
  });
}

export function useArchiveRequests() {
  return useQuery({
    queryKey: [KEY, "archive-requests"],
    queryFn: async () =>
      (await http.get<{ results: ArchiveRequest[] }>("/badms/archive_requests")).data,
  });
}

export function useSubmitArchiveRequest() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (form: FormData) =>
      (await http.post<ArchiveRequest>("/badms/archive_requests", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })).data,
    onSuccess: () => client.invalidateQueries({ queryKey: [KEY] }),
  });
}

export function useDecideArchiveRequest() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, decision }: { id: number; decision: "approve" | "reject" }) =>
      (await http.post<ArchiveRequest>(`/badms/archive_requests/${id}/decision`, {
        decision,
      })).data,
    onSuccess: () => client.invalidateQueries({ queryKey: [KEY] }),
  });
}
