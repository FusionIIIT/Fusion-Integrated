export type FileStatus = 'draft' | 'circulated' | 'archived';

export type FileSummary = {
  id: number;
  subject: string;
  status: FileStatus;
  owner_name: string;
  holder_name: string | null;
  updated_at: string;
};

export type FilePermissions = {
  can_edit_draft: boolean;
  can_forward: boolean;
  can_return: boolean;
  can_archive: boolean;
};

export type FileDetail = {
  status: FileStatus;
  owner_name: string;
  holder_name: string | null;
  id: number;
  subject: string;
  comment: string;
  attachments: string[];
  permissions: FilePermissions;
  created_at: string;
  updated_at: string;
};

export type HistoryEventType = 'created' | 'edited' | 'forwarded' | 'returned' | 'archived';

export type HistoryEvent = {
  id: number;
  event: HistoryEventType;
  sender_name: string;
  receiver_name: string | null;
  comment: string;
  attachments: string[];
  created_at: string;
};

export type Recipient = {
  id: number;
  name: string;
  designation: string;
};

export type CreateFileInput = {
  subject: string;
  comment: string;
};

export type UpdateFileInput = {
  subject?: string;
  comment?: string;
};

export type ForwardInput = {
  recipient_id: number;
  comment: string;
};

export type MovementCommentInput = {
  comment: string;
};
