import { http } from "../../lib/http";
import type { EmployeeUser, FTSFile, FTSFileDetail, FileMovement } from "./types";

export interface CreateFileInput {
  subject: string;
  description?: string;
  initial_comment: string;
  is_draft?: boolean;
  receiver_id?: number | null;
  receiver_designation?: string;
  attachments?: Array<{
    file_name: string;
    file_path?: string;
    file_size?: number;
    mime_type?: string;
  }>;
}

export interface EditDraftInput {
  subject?: string;
  description?: string;
  comment?: string;
  attachments?: Array<{
    file_name: string;
    file_path?: string;
    file_size?: number;
    mime_type?: string;
  }>;
}

export interface ForwardFileInput {
  receiver_id: number;
  receiver_designation?: string;
  remarks: string;
  attachments?: Array<{
    file_name: string;
    file_path?: string;
    file_size?: number;
    mime_type?: string;
  }>;
}

export interface ReturnFileInput {
  remarks: string;
  attachments?: Array<{
    file_name: string;
    file_path?: string;
    file_size?: number;
    mime_type?: string;
  }>;
}

export const ftsApi = {
  getInbox: () => http.get<FTSFile[]>("/fts/inbox/").then((r) => r.data),
  getOutbox: () => http.get<FTSFile[]>("/fts/outbox/").then((r) => r.data),
  getDrafts: () => http.get<FTSFile[]>("/fts/drafts/").then((r) => r.data),
  getFile: (id: string | number) => http.get<FTSFileDetail>(`/fts/files/${id}/`).then((r) => r.data),
  createFile: (payload: CreateFileInput) =>
    http.post<FTSFileDetail>("/fts/files/", payload).then((r) => r.data),
  editDraft: (id: string | number, payload: EditDraftInput) =>
    http.patch<FTSFileDetail>(`/fts/files/${id}/draft/`, payload).then((r) => r.data),
  discardDraft: (id: string | number) => http.delete(`/fts/files/${id}/draft/`),
  forwardFile: (id: string | number, payload: ForwardFileInput) =>
    http.post<FileMovement>(`/fts/files/${id}/forward/`, payload).then((r) => r.data),
  returnFile: (id: string | number, payload: ReturnFileInput) =>
    http.post<FileMovement>(`/fts/files/${id}/return/`, payload).then((r) => r.data),
  archiveFile: (id: string | number, remarks: string) =>
    http.post<FTSFileDetail>(`/fts/files/${id}/archive/`, { remarks }).then((r) => r.data),
  searchEmployees: (q: string) =>
    http
      .get<EmployeeUser[]>(`/fts/users/search/?q=${encodeURIComponent(q)}`)
      .then((r) => r.data),
};
