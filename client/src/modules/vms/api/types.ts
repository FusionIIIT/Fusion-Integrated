export type RequestStatus =
  | "NOT_SUBMITTED"
  | "PENDING_HOST_APPROVAL"
  | "APPROVED"
  | "REJECTED"
  | "CANCELLED"
  | "EXPIRED"
  | "COMPLETED";

export type PassStatus = "ACTIVE" | "EXPIRED" | "DEACTIVATED" | "COMPLETED";
export type VisitStatus = "ON_SITE" | "COMPLETED" | "FLAGGED";

export interface Visitor {
  visitor_id: string;
  full_name: string;
  email: string;
  phone: string;
  id_document_type: string;
  id_document_number: string;
  organization?: string;
}

export interface Host {
  host_id: string;
  user_id: number;
  employee_id?: string;
  full_name: string;
  department?: string;
  designation?: string;
  email: string;
  office_location?: string;
}

export interface VisitRequest {
  request_id: string;
  visitor: Visitor;
  host: Host;
  purpose: string;
  scheduled_start_time: string;
  scheduled_end_time: string;
  status: RequestStatus;
  submission_timestamp: string;
  remarks?: string;
}

export interface VisitorPass {
  pass_id: string;
  request_id: string;
  visitor_name: string;
  host_name: string;
  pass_type: string;
  credential_data: string;
  valid_from: string;
  valid_until: string;
  status: PassStatus;
  permitted_zones: string[];
}

export interface VisitLog {
  log_id: string;
  visitor_pass_id: string;
  visitor_name: string;
  entry_gate_id: string;
  entry_gate_name: string;
  exit_gate_id?: string;
  exit_gate_name?: string;
  check_in_time: string;
  check_out_time?: string;
  status: VisitStatus;
  verifier_notes?: string;
}

export interface Gate {
  gate_id: string;
  gate_name: string;
  gate_type: string;
  location_zone: string;
  is_operational: boolean;
}
