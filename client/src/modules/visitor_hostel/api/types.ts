export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface Booking {
  id: number;
  status: string;
  is_offline: boolean;
  source: string;
  indenter_user_id: number | null;
  visitor_name: string;
  visitor_phone: string;
  visitor_email: string;
  visitor_organization: string;
  visitor_address: string;
  purpose: string;
  category: "A" | "B" | "C" | "D";
  occupancy: "single" | "double" | "suite";
  arrival_date: string;
  arrival_time: string | null;
  departure_date: string;
  departure_time: string | null;
  rooms_required: number;
  occupants: number;
  billing_responsibility: "visitor" | "indenter" | "institute" | "project";
  billing_reference: string;
  decision_reason: string;
  checked_in_at: string | null;
  checked_out_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Room {
  id: number;
  number: string;
  room_type: string;
  floor: string;
  is_active: boolean;
}

export interface InventoryItem {
  id: number;
  name: string;
  kind: string;
  unit: string;
  quantity: number;
  min_threshold: number;
  is_active: boolean;
  below_threshold: boolean;
  updated_at: string;
}

export interface Replenishment {
  id: number;
  item: InventoryItem;
  quantity_required: number;
  note: string;
  status: "requested" | "approved";
  created_at: string;
  approved_at: string | null;
}
