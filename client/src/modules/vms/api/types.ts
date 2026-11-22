/** TypeScript wire types mirroring VMS API serializers. */

export interface Visitor {
  id: number;
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  id_type: string;
  id_number_hash: string;
  organization?: string;
  is_active: boolean;
}

export interface Visit {
  id: number;
  pass_number: string;
  qr_code_hash: string;
  visitor: Visitor;
  host_user_id: number;
  purpose: string;
  visit_type: "pre_registered" | "walk_in" | "vip" | "contractor";
  status: "requested" | "approved" | "rejected" | "on_site" | "completed" | "cancelled" | "expired";
  valid_from: string;
  valid_to: string;
  allowed_zones: string[];
  is_multi_entry: boolean;
  check_in_time: string | null;
  check_out_time: string | null;
  rejection_reason?: string;
  created_at: string;
}

export interface VisitRequestPayload {
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  id_type: string;
  id_number: string;
  organization?: string;
  host_user_id: number;
  purpose: string;
  valid_from: string;
  valid_to: string;
  allowed_zones?: string[];
  visit_type?: string;
  is_multi_entry?: boolean;
}

export interface QRScanPayload {
  qr_code_hash: string;
  gate_name?: string;
  reader_machine_id?: string;
}

export interface GateAlert {
  id: number;
  alert_type: string;
  severity: "info" | "warning" | "critical";
  message: string;
  status: "open" | "resolved";
  visit_id: number | null;
  created_at: string;
}

export interface EmergencyMuster {
  id: number;
  muster_code: string;
  status: "active" | "resolved";
  headcount_total: number;
  headcount_accounted: number;
  started_at: string;
  ended_at: string | null;
}
