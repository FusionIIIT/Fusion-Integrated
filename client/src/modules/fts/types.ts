export type FileStatus = "draft" | "circulating" | "archived" | "discarded";

export interface FileMovement {
  id: number;
  sequence_number: number;
  sender_id: number;
  sender_designation: string;
  receiver_id: number;
  receiver_designation: string;
  action: "created" | "forwarded" | "returned" | "archived";
  remarks: string;
  created_at: string;
}

export interface FileComment {
  id: number;
  author_id: number;
  author_designation: string;
  comment_text: string;
  created_at: string;
}

export interface FileAttachment {
  id: number;
  uploader_id: number;
  file_name: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  created_at: string;
}

export interface FTSFile {
  id: number;
  file_id: string;
  subject: string;
  description: string;
  status: FileStatus;
  creator_id: number;
  creator_designation: string;
  owner_id: number;
  current_holder_id: number | null;
  current_holder_designation: string;
  created_at: string;
  updated_at: string;
}

export interface FTSFileDetail extends FTSFile {
  movements: FileMovement[];
  comments: FileComment[];
  attachments: FileAttachment[];
}

export interface EmployeeUser {
  user_id: number;
  username: string;
  display_name: string;
  kind: string;
  department: string;
}
