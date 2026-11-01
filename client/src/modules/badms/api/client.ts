import { http } from "../../../lib/http";

export type BackupRun = {
  id: number; trigger: string; status: string; artifact_url: string | null;
  checksum: string; size_bytes: number; message: string; started_at: string;
  finished_at: string | null;
};

export type ArchiveRequest = {
  id: number; department: string; file_name: string; data_date: string;
  owners: string; file_type: string; reason: string; attachment: string;
  initial_classification: string; classification: string; status: string;
  decision_note: string; created_at: string;
};

export type AuditEvent = {
  id: number; actor_id: number | null; action: string; object_type: string;
  object_id: string; outcome: string; details: Record<string, unknown>;
  created_at: string;
};

export async function getBackups() {
  return (await http.get<BackupRun[]>("/badms/backups/")).data;
}
export async function runBackup() {
  return (await http.post<BackupRun>("/badms/backups/run/")).data;
}
export async function getArchives() {
  return (await http.get<ArchiveRequest[]>("/badms/archives/")).data;
}
export async function submitArchive(form: FormData) {
  return (await http.post<ArchiveRequest>("/badms/archives/", form)).data;
}
export async function decideArchive(id: number, action: "approve" | "reject") {
  return (await http.post<ArchiveRequest>(`/badms/archives/${id}/decision/`, { action })).data;
}
export async function classifyArchive(id: number, classification: string) {
  return (await http.post<ArchiveRequest>(`/badms/archives/${id}/classification/`, { classification })).data;
}
export async function completeSensitiveArchive(id: number) {
  return (await http.post<ArchiveRequest>(`/badms/archives/${id}/complete-sensitive/`, {})).data;
}
export async function getAudit() {
  return (await http.get<AuditEvent[]>("/badms/audit/")).data;
}
