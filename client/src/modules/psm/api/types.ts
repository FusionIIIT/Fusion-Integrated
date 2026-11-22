/** Wire types for the Purchase & Stores Management (PSM) API. */

export interface ItemMaster {
  id: number;
  item_code: string;
  name: string;
  category: "CONSUMABLE" | "NON_CONSUMABLE" | "EQUIPMENT" | "SERVICE";
  unit_of_measure: string;
  standard_rate: string;
  description: string;
  created_at: string;
}

export interface IndentItem {
  id?: number;
  item_master?: ItemMaster;
  item_master_id?: number;
  quantity_requested: number;
  estimated_unit_cost: string;
  line_total?: string;
  specifications: string;
}

export interface Indent {
  id: number;
  indent_number: string;
  user_id: number;
  department_code: string;
  title: string;
  purpose: string;
  priority: "LOW" | "STANDARD" | "URGENT";
  status:
    | "DRAFT"
    | "SUBMITTED"
    | "PENDING_DEPT_APPROVAL"
    | "PENDING_PS_REVIEW"
    | "PENDING_DIRECTOR_APPROVAL"
    | "APPROVED"
    | "REJECTED"
    | "FULFILLED"
    | "CANCELLED";
  estimated_total: string;
  rejection_reason?: string;
  submitted_at?: string;
  approved_at?: string;
  created_at: string;
  items: IndentItem[];
}

export interface Vendor {
  id: number;
  vendor_code: string;
  name: string;
  contact_person: string;
  email: string;
  phone: string;
  address: string;
  bank_account_number: string;
  bank_ifsc: string;
  status: "DRAFT" | "SUBMITTED" | "VERIFIED" | "SUSPENDED" | "BLACKLISTED";
  verified_by_user_id?: number;
  verified_at?: string;
  created_at: string;
}

export interface POLineItem {
  id: number;
  item_master: ItemMaster;
  quantity_ordered: number;
  quantity_delivered: number;
  unit_price: string;
  line_total: string;
}

export interface PurchaseOrder {
  id: number;
  po_number: string;
  indent: Indent;
  vendor: Vendor;
  procurement_method: "DIRECT" | "QUOTATION" | "TENDER" | "GEM";
  status: "DRAFT" | "ISSUED" | "PARTIALLY_DELIVERED" | "COMPLETED" | "CANCELLED";
  total_amount: string;
  delivery_due_date?: string;
  issued_at?: string;
  created_at: string;
  lines: POLineItem[];
}

export interface GRNItem {
  id: number;
  po_line_item: POLineItem;
  quantity_received: number;
  quantity_accepted: number;
  quantity_rejected: number;
  remarks: string;
}

export interface GoodsReceiptNote {
  id: number;
  grn_number: string;
  purchase_order: PurchaseOrder;
  store_keeper_user_id: number;
  challan_number: string;
  invoice_number: string;
  receipt_date: string;
  status: "INSPECTION_PENDING" | "ACCEPTED" | "DISCREPANT" | "CLOSED";
  indentor_acknowledged: boolean;
  indentor_acknowledged_at?: string;
  notes: string;
  created_at: string;
  items: GRNItem[];
}

export interface StockItem {
  id: number;
  item_master: ItemMaster;
  item_code: string;
  item_name: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  available_quantity: number;
  reorder_level: number;
  created_at: string;
}

export interface DiscrepancyReport {
  id: number;
  discrepancy_code: string;
  grn: GoodsReceiptNote;
  grn_number?: string;
  reported_by_user_id: number;
  discrepancy_type: string;
  details: string;
  status: "OPEN_HOLD_PAYMENT" | "RESOLVED";
  resolution_summary?: string;
  resolved_at?: string;
  created_at: string;
}
