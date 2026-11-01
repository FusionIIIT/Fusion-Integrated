export interface Announcement {
  id: number;
  title: string;
  body: string;
  target_roles: string[];
  target_programmes: string[];
  target_years: number[];
  status: "active" | "hidden" | "deleted";
  published_by_user_id: number;
  published_by_role: string;
  created_at: string;
  updated_at: string;
}

export interface InventoryItem {
  id: number;
  name: string;
  category: string;
  unit: string;
  quantity: number;
}

export type StockStatus = "pending_hod" | "approved" | "rejected" | "issued";

export interface StockRequest {
  id: number;
  item: number;
  item_name: string;
  unit: string;
  requested_by_user_id: number;
  quantity: number;
  purpose: string;
  status: StockStatus;
  decision_note: string;
  decided_at: string | null;
  issued_at: string | null;
  created_at: string;
}

export interface StockMovement {
  id: number;
  item_name: string;
  kind: "insert" | "issue";
  quantity: number;
  actor_user_id: number;
  recipient_user_id: number | null;
  at: string;
}

export type FeedbackStatus = "new" | "under_review" | "resolved" | "closed";

export interface Feedback {
  id: number;
  subject: string;
  body: string;
  category: string;
  status: FeedbackStatus;
  resolution_note: string;
  submitted_by_role: string;
  created_at: string;
}
