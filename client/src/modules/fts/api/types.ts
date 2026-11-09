/** Types mirror the FTS backend (modules/fts) exactly. Employee ids are
 *  strings, and the status vocabulary is the backend's, not the spec prose. */

export type FileStatus =
  | "draft" | "in_transit" | "received" | "returned" | "archived";

export type Priority = "low" | "medium" | "high" | "urgent";

/** Rows of GET /fts/files/inbox/ and /outbox/. */
export interface FileSummary {
  id: number;
  uin: string;
  subject: string;
  priority: Priority;
  category: string;
  status: FileStatus;
  creator_id: string;
  current_holder_id: string;
  updated_at: string | null;
}

/** Rows of GET /fts/files/drafts/. */
export interface DraftSummary {
  id: number;
  uin: string;
  subject: string;
  description: string;
  priority: Priority;
  category: string;
  status: FileStatus;
  created_at: string | null;
  updated_at: string | null;
}

/** GET /fts/files/{id}/ (FTSFileSerializer). */
export interface FileDetail {
  id: number;
  uin: string;
  subject: string;
  description: string;
  priority: Priority;
  category: string;
  status: FileStatus;
  creator_id: string;
  creator_role: string;
  current_holder_id: string;
  current_holder_role: string;
  is_draft: boolean;
  created_at: string;
  updated_at: string;
}

export type MovementAction = "created" | "forwarded" | "returned" | "archived";

export interface HistoryComment {
  author_id: string;
  author_role: string;
  remarks: string;
  created_at: string | null;
}

/** One entry of GET /fts/files/{id}/history/, oldest first. */
export interface HistoryMovement {
  movement_id: number;
  action: MovementAction;
  from_user_id: string;
  from_role: string;
  to_user_id: string;
  to_role: string;
  created_at: string | null;
  comments: HistoryComment[];
}

export interface CreateDraftInput {
  subject: string;
  initial_comment: string;
  description: string;
  priority: Priority;
  category: string;
  creator_role: string;
}

export interface ForwardInput {
  receiver_id: string;
  /** Omit when unknown: the backend rejects a blank string. */
  receiver_role?: string;
  comment: string;
  sender_role: string;
}

export interface ReturnInput {
  comment: string;
  sender_role: string;
  target_receiver_id?: string;
}

export interface ArchiveInput {
  remarks: string;
  user_role: string;
}

export interface CreateDraftResult {
  file_id: number;
  uin: string;
  subject: string;
  status: FileStatus;
  is_draft: boolean;
}

export interface MovementResult {
  file_id: number;
  uin: string;
  new_status: FileStatus;
  movement_id: number;
  current_holder_id?: string;
  returned_to_id?: string;
}

export interface ArchiveResult {
  file_id: number;
  uin: string;
  status: FileStatus;
  archived_by: string;
}
