/**
 * Type definitions for Purchase and Stores Management (PSM).
 * RULE: All monetary values (estimated_cost, total_cost, etc.) MUST be typed as string.
 */

export type IndentStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "STOCK_CHECKED"
  | "DEPT_REVIEWED"
  | "HEAD_RECOMMENDED"
  | "AWAITING_FINAL_APPROVAL"
  | "APPROVED"
  | "REJECTED"
  | "WITHDRAWN";

export type Priority = "NORMAL" | "HIGH" | "CRITICAL";

export type ProcurementMethod = "DIRECT" | "TENDER";

export type POStatus = "ISSUED" | "DELIVERED" | "CANCELLED";

export type TransferStatus = "REQUESTED" | "DISPATCHED" | "COMPLETED";

export interface Indent {
  id: number;
  indent_id: string;
  requestor_id: number;
  item_details: string;
  quantity: number;
  /** Monetary amount stored as exact string */
  estimated_cost: string;
  justification: string;
  status: IndentStatus;
  priority: Priority;
  is_duplicate: boolean;
  rejection_justification?: string | null;
  current_version: number;
  created_at: string;
  updated_at: string;
}

export interface IndentVersion {
  id: number;
  version_number: number;
  item_details: string;
  quantity: number;
  estimated_cost: string;
  justification: string;
  created_at: string;
}

export interface Vendor {
  id: number;
  name: string;
  gst_number: string;
  bank_account_number: string;
  bank_ifsc: string;
  compliance_docs_url?: string | null;
  is_verified: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface PurchaseOrder {
  id: number;
  po_number: string;
  indent: number;
  indent_business_id?: string;
  vendor: number;
  vendor_name?: string;
  procurement_method: ProcurementMethod;
  status: POStatus;
  /** Monetary total stored as string */
  total_cost: string;
  delivery_schedule: string;
  created_at: string;
  updated_at: string;
}

export interface GoodsReceiptNote {
  id: number;
  grn_number: string;
  purchase_order: number;
  po_number?: string;
  accepted_quantity: number;
  rejected_quantity: number;
  inspection_remarks: string;
  is_confirmed: boolean;
  has_discrepancy: boolean;
  created_at: string;
  updated_at: string;
}

export interface StockItem {
  id: number;
  item_code: string;
  name: string;
  description: string;
  department: string;
  central_stock: number;
  department_stock: number;
  reserved_stock: number;
  allocable_stock: number;
  created_at: string;
  updated_at: string;
}

export interface StockTransfer {
  id: number;
  transfer_id: string;
  source_department: string;
  destination_department: string;
  stock_item: number;
  item_code?: string;
  item_name?: string;
  quantity: number;
  status: TransferStatus;
  created_at: string;
  updated_at: string;
}

// -- Mutation Payloads --

export interface CreateIndentPayload {
  item_details: string;
  quantity: number;
  estimated_cost: string;
  justification: string;
  priority?: Priority;
  status?: "DRAFT" | "SUBMITTED";
}

export interface ModifyIndentPayload {
  item_details?: string;
  quantity?: number;
  estimated_cost?: string;
  justification?: string;
  priority?: Priority;
}

export interface UpdateIndentStatusPayload {
  target_state: IndentStatus;
  justification?: string;
}

export interface CreateVendorPayload {
  name: string;
  gst_number: string;
  bank_account_number: string;
  bank_ifsc: string;
  compliance_docs_url?: string;
}

export interface CreatePOPayload {
  indent_id: number;
  vendor_id: number;
  procurement_method: ProcurementMethod;
  total_cost: string;
  delivery_schedule: string;
}

export interface RecordGRNPayload {
  purchase_order_id: number;
  accepted_quantity: number;
  rejected_quantity?: number;
  inspection_remarks?: string;
}

export interface CreateTransferPayload {
  source_department: string;
  destination_department: string;
  stock_item_id: number;
  quantity: number;
}
