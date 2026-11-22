export interface Complaint {
  id: number;
  complaint_id: string;
  complainant_user_id: number;
  category: "civil" | "electrical";
  location: string;
  urgency: "low" | "medium" | "high" | "emergency";
  remarks: string;
  status: string;
  assigned_engineer_id: number | null;
  is_urgent_escalated: boolean;
  created_at: string;
}

export interface InventoryItem {
  id: number;
  item_code: string;
  name: string;
  category: string;
  unit: string;
  current_stock: number;
}
