/**
 * Generic type for paginated API responses.
 * @template T The type of the items in the results array.
 */
export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

/**
 * Type for a Department Announcement.
 */
export interface Announcement {
  id: number;
  department: string;
  title: string;
  body: string;
  target_roles: string[];
  target_programme: string | null;
  target_batch_year: number | null;
  status: string;
}

/**
 * Type for a Stock Request.
 */
export interface StockRequest {
  id: number;
  department: string;
  item: string;
  requester_user_id: number;
  quantity: number;
  state: string;
}

/**
 * Type for an Inventory Item.
 */
export interface InventoryItem {
  id: number;
  department: string;
  name: string;
  unit: string;
  quantity: number;
}

/**
 * Type for a Feedback submission.
 */
export interface Feedback {
  id: number;
  department: string;
  submitter_user_id: number;
  body: string;
  category: string;
  state: string;
  created_at: string;
}

/**
 * Type for a Timetable Slot.
 */
export interface TimetableSlot {
  id: number;
  department: string;
  slot_kind: string;
  weekday: string;
  start_time: string;
  end_time: string;
  room: string;
  programme: string;
  batch_year: number;
  title: string;
}
