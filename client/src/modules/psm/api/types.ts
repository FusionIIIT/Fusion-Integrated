// TypeScript interfaces mirroring modules/psm/api/serializers.py.
export interface Page<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ListResult<T> {
  results: T[];
}

export interface DashboardSummary {
  active_role: string;
  indents_total: number;
  indents_pending_approval: number;
  indents_by_status: Record<string, number>;
  purchase_orders_total: number;
  purchase_orders_by_status: Record<string, number>;
  open_discrepancies: number;
  pending_transfers: number;
  invoices_on_hold: number;
  invoices_pending_payment: number;
}

export interface Indent {
  id: number;
  indent_number: string | null;
  user_id: number;
  department: string;
  item_id: number | null;
  item_description: string;
  quantity: number;
  estimated_cost: string;
  justification: string;
  priority: "normal" | "high" | "critical";
  status: string;
  procurement_method: string;
  is_duplicate_flagged: boolean;
  duplicate_of_indent_id: number | null;
  duplicate_reviewed: boolean;
  version: number;
  submitted_at: string | null;
  rejection_reason: string;
  created_at: string;
}

export interface IndentDetail extends Indent {
  versions: Array<{
    version: number;
    snapshot: Record<string, unknown>;
    actor_user_id: number;
    created_at: string;
  }>;
  transitions: Array<{
    from_status: string;
    to_status: string;
    actor_user_id: number | null;
    actor_role: string;
    reason: string;
    created_at: string;
  }>;
}

export interface StockItem {
  id: number;
  sku: string;
  name: string;
  category: string;
  unit: string;
  description: string;
  is_active: boolean;
}

export interface StockLocation {
  id: number;
  code: string;
  name: string;
  department: string;
  is_central: boolean;
}

export interface StockAvailability {
  item_id: number;
  sku: string;
  item_name: string;
  unit: string;
  location_id: number;
  location_code: string;
  location_name: string;
  department: string;
  is_central: boolean;
  on_hand: number;
  reserved: number;
  allocable: number;
}

export interface InternalIssue {
  id: number;
  indent_id: number;
  indent_number: string | null;
  item_description: string;
  quantity: number;
  location_id: number;
  location_code: string;
  status: string;
  picking_scheduled_at: string | null;
  dispatch_scheduled_at: string | null;
  dispatched_at: string | null;
}

export interface StockTransfer {
  id: number;
  transfer_number: string;
  item_id: number;
  item_name: string;
  source_location_id: number;
  source_location_code: string;
  destination_location_id: number;
  destination_location_code: string;
  quantity: number;
  status: string;
  notes: string;
  dispatched_at: string | null;
  confirmed_at: string | null;
  created_at: string;
}

export interface Vendor {
  id: number;
  code: string;
  name: string;
  gstin: string;
  bank_account_number: string;
  bank_ifsc: string;
  bank_name: string;
  compliance_documents: string[];
  contact_email: string;
  is_verified: boolean;
  verified_at: string | null;
  version: number;
  is_active: boolean;
}

export interface TenderBid {
  id: number;
  vendor_id: number;
  vendor_name: string;
  quoted_amount: string;
  technical_score: string | null;
  financial_score: string | null;
  evaluation_notes: string;
  is_selected: boolean;
}

export interface Tender {
  id: number;
  tender_number: string;
  indent_id: number;
  title: string;
  scope: string;
  evaluation_criteria: string;
  submission_deadline: string;
  status: string;
  committee_members: string[];
  committee_minutes: string;
  awarded_vendor_id: number | null;
  bids: TenderBid[];
}

export interface PurchaseOrder {
  id: number;
  po_number: string;
  indent_id: number;
  indent_number: string | null;
  vendor_id: number;
  vendor_name: string;
  tender_id: number | null;
  ordered_quantity: number;
  unit_price: string;
  total_amount: string;
  status: string;
  planned_delivery_date: string;
  actual_delivery_date: string | null;
  delivery_notes: string;
  issued_at: string;
}

export interface GoodsReceiptNote {
  id: number;
  grn_number: string;
  purchase_order_id: number | null;
  internal_issue_id: number | null;
  replacement_for_case_id: number | null;
  inspected_by_user_id: number;
  received_quantity: number;
  accepted_quantity: number;
  rejected_quantity: number;
  inspection_notes: string;
  status: string;
  confirmed_by_user_id: number | null;
  confirmed_at: string | null;
  stock_posted: boolean;
  created_at: string;
}

export interface DiscrepancyCase {
  id: number;
  case_number: string;
  grn_id: number;
  reported_by_user_id: number;
  discrepancy_type: string;
  affected_quantity: number;
  description: string;
  evidence_url: string;
  evidence_filename: string;
  requested_resolution: string;
  status: string;
  replacement_count: number;
  resolution_notes: string;
  inventory_adjusted: boolean;
  accounting_adjusted: boolean;
  communications: Array<{
    id: number;
    sender_label: string;
    message: string;
    recorded_by_user_id: number;
    created_at: string;
  }>;
  created_at: string;
}

export interface PaymentTransaction {
  id: number;
  amount: string;
  payment_reference: string;
  is_partial: boolean;
  status: string;
  processed_by_user_id: number;
  notes: string;
  created_at: string;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  purchase_order_id: number;
  po_number: string;
  vendor_id: number;
  vendor_name: string;
  billed_quantity: number;
  billed_amount: string;
  eligible_amount: string;
  status: string;
  hold_reason: string;
  verified_at: string | null;
  payments: PaymentTransaction[];
}

export interface ReportResult {
  log_id: number;
  report_type: string;
  headers: string[];
  rows: Array<Record<string, string | number>>;
  row_count: number;
}

export interface ReportSchedule {
  id: number;
  name: string;
  report_type: string;
  filters: Record<string, string>;
  cadence: string;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string;
}

export interface AuditLog {
  id: number;
  actor_user_id: number | null;
  actor_role: string;
  action: string;
  target_type: string;
  target_id: number;
  from_state: string;
  to_state: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface PsmNotification {
  id: number;
  topic: string;
  subject: string;
  body: string;
  status: string;
  sent_at: string | null;
  created_at: string;
}

export interface PsmPolicy {
  id: number;
  version: number;
  effective_from: string;
  is_active: boolean;
  direct_limit: string;
  final_approval_threshold: string;
  high_priority_direct_allowed: boolean;
  modifiable_states: string[];
  withdrawable_states: string[];
  sla_reminder_hours: number;
  sla_escalation_hours: number;
  high_priority_sla_reminder_hours: number;
  high_priority_sla_escalation_hours: number;
  partial_payment_enabled: boolean;
  duplicate_window_days: number;
}
