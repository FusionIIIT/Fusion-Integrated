export type FileStatus = 'active' | 'inactive' | 'deleted';

export type FileSummary = {
  id: number;
  subject: string;
  status: FileStatus;
  created_at: Date;
  updated_at: Date;
};

export type FilePermissions = {
  read: boolean;
  write: boolean;
  delete: boolean;
};

export type FileDetail = {
  id: number;
  subject: string;
  content: string;
  status: FileStatus;
  permissions: FilePermissions;
  created_at: Date;
  updated_at: Date;
};

export type HistoryEventType = 'created' | 'updated' | 'deleted' | 'moved';

export type HistoryEvent = {
  id: number;
  file_id: number;
  event_type: HistoryEventType;
  details: string;
  created_at: Date;
};

export type Recipient = {
  id: number;
  name: string;
  email: string;
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
