export interface TrackedFileSummary {
  id: number;
  file_number: string;
  subject: string;
  status: "draft" | "circulating" | "archived";
  created_by_user_id: number;
  creator_designation: string;
  current_holder_user_id: number | null;
  current_holder_designation: string;
  is_archived: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FileAttachment {
  id: number;
  file_id: number;
  file_name: string;
  file_size: number;
  mime_type: string;
  created_at: string;
}

export interface FileMovement {
  id: number;
  sequence_number: number;
  action: string;
  sender_user_id: number;
  sender_designation: string;
  receiver_user_id: number;
  receiver_designation: string;
  comment: string;
  created_at: string;
  attachments?: FileAttachment[];
}

export interface TrackedFileDetail extends TrackedFileSummary {
  description: string;
  movements: FileMovement[];
  attachments: FileAttachment[];
}

export interface FileAuditLog {
  id: number;
  file_id: number | null;
  action: string;
  actor_user_id: number;
  actor_designation: string;
  payload: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}
