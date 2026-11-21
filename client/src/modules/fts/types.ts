export interface UserSummary {
  user_id: number;
  username: string;
  first_name?: string;
  last_name?: string;
  email?: string;
}

export interface FileAttachment {
  id: number;
  file: number;
  movement?: number | null;
  uploader: number;
  file_name: string;
  file_url?: string;
  file_size: number;
  created_at: string;
}

export interface FileMovement {
  id: number;
  file: number;
  sender: UserSummary;
  sender_role?: string;
  receiver: UserSummary;
  receiver_role?: string;
  action: 'created' | 'forwarded' | 'returned' | 'archived';
  comments: string;
  attachments?: FileAttachment[];
  created_at: string;
}

export interface FileAuditLog {
  id: number;
  file: number;
  actor: UserSummary;
  actor_role?: string;
  action: string;
  details: string;
  created_at: string;
}

export interface FTSFile {
  id: number;
  file_number: string;
  subject: string;
  description?: string;
  owner: UserSummary;
  creator_role?: string;
  current_holder?: UserSummary | null;
  current_holder_role?: string;
  status: 'draft' | 'circulated' | 'archived' | 'discarded';
  is_archived: boolean;
  archived_at?: string | null;
  created_at: string;
  updated_at: string;
  movements?: FileMovement[];
  attachments?: FileAttachment[];
  audit_logs?: FileAuditLog[];
}

export interface CreateFilePayload {
  subject: string;
  description?: string;
  initial_comment: string;
  creator_role?: string;
}

export interface ForwardFilePayload {
  receiver_id: number;
  receiver_role?: string;
  sender_role?: string;
  comment: string;
}

export interface ReturnFilePayload {
  sender_role?: string;
  comment: string;
}

export interface ArchiveFilePayload {
  comment?: string;
  user_role?: string;
}