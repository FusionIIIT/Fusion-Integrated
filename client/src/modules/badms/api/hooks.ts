import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type {
  ArchiveRequest, AuditEvent, BackupRun, BackupSchedule, BadmsReport,
  RestoreRequest, SecurityPolicy, StorageExtension,
} from "./types";

const ROOT = "/badms";
const KEY = "badms";

function invalidate(qc: ReturnType<typeof useQueryClient>) {
  return qc.invalidateQueries({ queryKey: [KEY] });
}

export const useBackups = () =>
  useQuery({
    queryKey: [KEY, "backups"],
    queryFn: async () => (await http.get<BackupRun[]>(`${ROOT}/backups`)).data,
    refetchInterval: 15_000,
  });

export function useCreateBackup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (dataset_key: string) =>
      (await http.post<BackupRun>(`${ROOT}/backups`, { dataset_key })).data,
    onSuccess: () => invalidate(qc),
  });
}

export const useSchedules = () =>
  useQuery({
    queryKey: [KEY, "schedules"],
    queryFn: async () =>
      (await http.get<BackupSchedule[]>(`${ROOT}/schedules`)).data,
  });

export function useCreateSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<BackupSchedule>) =>
      (await http.post<BackupSchedule>(`${ROOT}/schedules`, body)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useUpdateSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: Partial<BackupSchedule> & { id: number }) =>
      (await http.patch<BackupSchedule>(`${ROOT}/schedules/${id}`, body)).data,
    onSuccess: () => invalidate(qc),
  });
}

export const useArchives = () =>
  useQuery({
    queryKey: [KEY, "archives"],
    queryFn: async () =>
      (await http.get<ArchiveRequest[]>(`${ROOT}/archives`)).data,
    refetchInterval: 15_000,
  });

export function useCreateArchive(special = false) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: FormData) =>
      (await http.post<ArchiveRequest>(
        special ? `${ROOT}/archives/special-operation` : `${ROOT}/archives`,
        body,
      )).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useArchiveDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, approved, reason }: {
      id: number; approved: boolean; reason?: string;
    }) =>
      (await http.post<ArchiveRequest>(`${ROOT}/archives/${id}/decision`,
        { approved, reason })).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useArchiveClassification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, classification }: {
      id: number; classification: string;
    }) =>
      (await http.post<ArchiveRequest>(
        `${ROOT}/archives/${id}/classification`, { classification },
      )).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useConfigureEncryption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<ArchiveRequest>(
        `${ROOT}/archives/${id}/encryption`, {},
      )).data,
    onSuccess: () => invalidate(qc),
  });
}

export const useRestores = () =>
  useQuery({
    queryKey: [KEY, "restores"],
    queryFn: async () =>
      (await http.get<RestoreRequest[]>(`${ROOT}/restores`)).data,
    refetchInterval: 15_000,
  });

export function useCreateRestore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { archive: number; reason: string }) =>
      (await http.post<RestoreRequest>(`${ROOT}/restores`, body)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useRestoreDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, approved }: { id: number; approved: boolean }) =>
      (await http.post<RestoreRequest>(
        `${ROOT}/restores/${id}/decision`, { approved },
      )).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useExecuteRestore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      try {
        const response = await http.post<Blob>(
          `${ROOT}/restores/${id}/execute`,
          {},
          { responseType: "blob" },
        );
        saveBlob(
          response.data,
          filenameFromDisposition(
            response.headers["content-disposition"], `restore-${id}.bin`,
          ),
        );
      } catch (error) {
        throw await readBlobError(error);
      }
    },
    onSuccess: () => invalidate(qc),
  });
}

export const useStorageExtensions = () =>
  useQuery({
    queryKey: [KEY, "storage-extensions"],
    queryFn: async () =>
      (await http.get<StorageExtension[]>(`${ROOT}/storage-extensions`)).data,
    refetchInterval: 15_000,
  });

export function useCreateStorageExtension() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { requested_bytes: number; justification: string }) =>
      (await http.post<StorageExtension>(`${ROOT}/storage-extensions`, body)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useStorageExtensionDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, approved, reason }: {
      id: number; approved: boolean; reason?: string;
    }) =>
      (await http.post<StorageExtension>(
        `${ROOT}/storage-extensions/${id}/decision`, { approved, reason },
      )).data,
    onSuccess: () => invalidate(qc),
  });
}

export const useAuditEvents = () =>
  useQuery({
    queryKey: [KEY, "audit"],
    queryFn: async () =>
      (await http.get<AuditEvent[]>(`${ROOT}/audit`)).data,
  });

export const useBadmsReport = () =>
  useQuery({
    queryKey: [KEY, "reports"],
    queryFn: async () =>
      (await http.get<BadmsReport>(`${ROOT}/reports`)).data,
  });

export const useSecurityPolicies = () =>
  useQuery({
    queryKey: [KEY, "security-policies"],
    queryFn: async () =>
      (await http.get<SecurityPolicy[]>(`${ROOT}/security-policies`)).data,
  });

export function useCreateSecurityPolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<SecurityPolicy>) =>
      (await http.post<SecurityPolicy>(`${ROOT}/security-policies`, body)).data,
    onSuccess: () => invalidate(qc),
  });
}
