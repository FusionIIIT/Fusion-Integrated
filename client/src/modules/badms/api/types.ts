export type Page<T> = { next: string | null; previous: string | null; results: T[] };

export type BackupRun = {
  id: number;
  trigger: string;
  status: string;
  dataset: string;
  started_at: string;
  completed_at: string | null;
  checksum_sha256: string;
  integrity_verified: boolean;
  outcome: string;
};

export type ArchiveRequest = {
  id: number;
  user_id: number;
  department: string;
  file_name: string;
  file_date: string;
  owners: string[];
  file_type: string;
  reason: string;
  initial_classification: string;
  classification: string;
  status: string;
  decision_note: string;
  checksum_sha256: string;
  created_at: string;
  updated_at: string;
};
