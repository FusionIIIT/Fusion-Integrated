/** Type definitions for the File Tracking System (FTS) module. */

export type FileStatus = "DRAFT" | "CIRCULATED" | "ARCHIVED" | "DISCARDED";
export type MovementType = "FORWARD" | "RETURN" | "ARCHIVE";

export interface FileAttachment {
  id: number;
  file_id: number;
  movement_id: number | null;
  uploader_user_id: number;
  uploader_username: string;
  file_name: string;
  file_url: string;
  file_size: number;
  mime_type: string;
  created_at: string;
}

export interface FileComment {
  id: number;
  file_id: number;
  movement_id: number | null;
  author_user_id: number;
  author_username: string;
  author_role: string;
  comment_text: string;
  created_at: string;
}

export interface FileMovement {
  id: number;
  file_id: number;
  sequence: number;
  movement_type: MovementType;
  from_user_id: number;
  from_username: string;
  from_role: string;
  to_user_id: number;
  to_username: string;
  to_role: string;
  comments: FileComment[];
  attachments: FileAttachment[];
  created_at: string;
}

export interface FileListItem {
  id: number;
  reference_number: string;
  subject: string;
  status: FileStatus;
  owner_user_id: number;
  owner_username: string;
  owner_role: string;
  current_holder_user_id: number | null;
  current_holder_username: string | null;
  current_holder_role: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface FileDetail extends FileListItem {
  description: string;
  comments: FileComment[];
  attachments: FileAttachment[];
  movements: FileMovement[];
}

export interface AttachmentPayload {
  file_name: string;
  file_url: string;
  file_size: number;
  mime_type: string;
}

export interface CreateFilePayload {
  subject: string;
  description?: string;
  comment: string;
  is_draft?: boolean;
  recipient_user_id?: number | null;
  recipient_username?: string;
  recipient_role?: string;
  attachments?: AttachmentPayload[];
}

export interface UpdateDraftPayload {
  subject?: string;
  description?: string;
  comment?: string;
  attachments?: AttachmentPayload[];
}

export interface ForwardFilePayload {
  to_user_id: number;
  to_username: string;
  to_role: string;
  comment: string;
  attachments?: AttachmentPayload[];
}

export interface ReturnFilePayload {
  comment: string;
  attachments?: AttachmentPayload[];
}

export interface FileAuditLog {
  id: number;
  file_id: number | null;
  action: string;
  actor_user_id: number;
  actor_username: string;
  actor_role: string;
  details: Record<string, unknown>;
  timestamp: string;
}

export interface UsageMetrics {
  total_files: number;
  draft_files: number;
  circulated_files: number;
  archived_files: number;
  discarded_drafts: number;
  total_movements: number;
}
