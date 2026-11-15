export interface CatalogueVersion {
  id: number;
  entry_id: number;
  entry_kind: "scholarship" | "award";
  version_number: number;
  configuration: Record<string, unknown>;
  effective_from: string | null;
  effective_to: string | null;
  application_opens_at: string | null;
  application_closes_at: string | null;
  status: string;
}

export interface Application {
  public_id: string;
  user_id: number;
  catalogue_version: number;
  kind: "scholarship" | "renewal";
  academic_cycle: string;
  state: string;
  application_data: Record<string, unknown>;
  submitted_at: string | null;
  created_at: string;
}

export interface StartApplicationRequest {
  catalogue_version_id: number;
  academic_cycle: string;
}

export interface SaveDraftRequest {
  public_id: string;
  application_data: Record<string, unknown>;
}
