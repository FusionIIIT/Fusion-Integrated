// TypeScript type definitions for the Visitors Hostel Management System (VHMS).

export type VisitorCategory = "A" | "B" | "C" | "D";
export type BillingResponsibility = "visitor" | "indenter" | "institute" | "project";
export type RoomType = "suite" | "non_suite";
export type OccupancyType = "single" | "double";
export type BookingStatus =
  | "pending"
  | "pending_offline"
  | "forwarded"
  | "forwarded_offline"
  | "approved"
  | "approved_offline"
  | "rejected"
  | "rejected_offline"
  | "room_allotted"
  | "checked_in"
  | "checked_out"
  | "cancellation_requested"
  | "cancelled";

export interface VisitorDetail {
  id?: number;
  name: string;
  email?: string;
  phone?: string;
  organization?: string;
  designation?: string;
  gender?: string;
}

export interface Room {
  id: number;
  room_number: string;
  room_type: RoomType;
  capacity: number;
  floor: number;
  is_active: boolean;
  remarks?: string;
}

export interface RoomAllotment {
  id: number;
  room: Room;
  occupancy_type: OccupancyType;
  allotted_by: number;
  allotted_at: string;
}

export interface Booking {
  id: number;
  booking_reference: string;
  indenter_id: number;
  is_offline: boolean;
  booking_source: "online" | "telephonic" | "walk_in";
  status: BookingStatus;
  visitor_category: VisitorCategory;
  visit_purpose: string;
  arrival_date: string;
  departure_date: string;
  checkin_time: string | null;
  checkout_time: string | null;
  number_of_rooms: number;
  number_of_occupants: number;
  billing_responsibility: BillingResponsibility;
  rejection_reason?: string;
  cancellation_reason?: string;
  cancellation_charge_percentage: string;
  cancellation_requested_at?: string | null;
  cancellation_confirmed_at?: string | null;
  visitors: VisitorDetail[];
  allotments: RoomAllotment[];
  created_at: string;
  updated_at: string;
}

export interface CreateBookingPayload {
  visitor_name: string;
  visitor_email?: string;
  visitor_phone?: string;
  visitor_category: VisitorCategory;
  visit_purpose: string;
  arrival_date: string;
  departure_date: string;
  number_of_rooms: number;
  number_of_occupants: number;
  billing_responsibility: BillingResponsibility;
  visitors?: VisitorDetail[];
}

export interface CreateOfflineBookingPayload extends CreateBookingPayload {
  booking_source: "telephonic" | "walk_in";
  indenter_id?: number;
}

export interface ModifyBookingPayload {
  visitor_category?: VisitorCategory;
  visit_purpose?: string;
  arrival_date?: string;
  departure_date?: string;
  number_of_rooms?: number;
  number_of_occupants?: number;
  billing_responsibility?: BillingResponsibility;
}

export interface RouteBookingPayload {
  action: "reject" | "forward";
  reason?: string;
}

export interface DecideBookingPayload {
  action: "approve" | "reject";
  reason?: string;
}

export interface CancelBookingPayload {
  reason: string;
}

export interface AllotRoomsPayload {
  room_ids: number[];
  occupancy_type: OccupancyType;
}

export interface CheckInPayload {
  checkin_time?: string;
}

export interface CheckOutPayload {
  checkout_time?: string;
  verified_by_guest: boolean;
}

export type MealOption = "full_day" | "individual" | "add_on";

export interface MealBooking {
  id: number;
  booking: number;
  meal_date: string;
  meal_option: MealOption;
  individual_type?: string;
  add_on_type?: string;
  quantity: number;
  rate: string;
  amount: string;
  booked_at: string;
}

export interface BookMealPayload {
  meal_date: string;
  meal_option: MealOption;
  individual_type?: string;
  add_on_type?: string;
  quantity: number;
}

export interface BillLineItem {
  id: number;
  item_type: "room" | "meal" | "cancellation" | "tax";
  description: string;
  quantity: string;
  unit_price: string;
  total_price: string;
}

export interface BillSettlement {
  id: number;
  payment_mode: "offline_cash";
  amount_paid: string;
  settled_by: number;
  settled_at: string;
  receipt_number: string;
  notes?: string;
}

export interface Bill {
  id: number;
  booking: number;
  bill_number: string;
  visitor_category: VisitorCategory;
  room_rent_total: string;
  meal_charge_total: string;
  cancellation_charge_total: string;
  total_amount: string;
  billing_responsibility: BillingResponsibility;
  status: "generated" | "verified" | "settled";
  is_immutable: boolean;
  finalized_at?: string | null;
  verified_by?: number | null;
  verified_at?: string | null;
  items: BillLineItem[];
  settlement?: BillSettlement | null;
  created_at: string;
  updated_at: string;
}

export interface SettleBillPayload {
  amount_paid: string;
  receipt_number: string;
  notes?: string;
}

export interface TariffConfig {
  id: number;
  category: VisitorCategory;
  room_type: RoomType;
  occupancy: OccupancyType;
  daily_rate: string;
  effective_from: string;
  is_active: boolean;
}

export interface InventoryItem {
  id: number;
  item_name: string;
  category: "linen" | "toiletries" | "crockery" | "utensils" | "cleaning" | "miscellaneous";
  current_quantity: number;
  minimum_threshold: number;
  unit: string;
  is_threshold_alert: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryReplenishment {
  id: number;
  item: InventoryItem;
  requested_quantity: number;
  status: "pending" | "approved" | "rejected";
  requested_by: number;
  approved_by?: number | null;
  approved_at?: string | null;
  remarks?: string;
  created_at: string;
}

export interface ReplenishRequestPayload {
  requested_quantity: number;
  remarks?: string;
}

export interface ReplenishApprovePayload {
  decision: "approved" | "rejected";
  remarks?: string;
}

export interface ReassignRolePayload {
  role_name: "caretaker" | "incharge";
  new_user_id: number;
  valid_from?: string;
  valid_to?: string;
}

export interface DailyOccupancyReport {
  date: string;
  total_rooms_occupied: number;
  total_occupants: number;
  rooms: {
    room_number: string;
    room_type: string;
    occupancy_type: string;
    booking_reference: string;
  }[];
}

export interface ArrivalsDeparturesReport {
  date: string;
  arrivals_count: number;
  departures_count: number;
  arrivals: {
    id: number;
    booking_reference: string;
    visitor_category: string;
    status: string;
  }[];
  departures: {
    id: number;
    booking_reference: string;
    status: string;
  }[];
}

export interface PendingApprovalsReport {
  pending_caretaker_review: number;
  forwarded_to_incharge: number;
  pending_cancellations: number;
}

export interface StayExceptionLog {
  id: number;
  booking_reference: string;
  alert_type: string;
  status: string;
  details: string;
  triggered_at: string;
}

export interface BookingSummaryReport {
  total_bookings: number;
  offline_bookings: number;
  status_distribution: Record<string, number>;
}

export interface CategoryOccupancyItem {
  visitor_category: string;
  total_stays: number;
  total_occupants: number;
}

export interface RevenueSummaryReport {
  total_billed: number;
  room_rent_total: number;
  meal_charge_total: number;
  cancellation_charge_total: number;
  settled_total: number;
}

export interface InventoryUsageItem {
  id: number;
  item_name: string;
  category: string;
  current_quantity: number;
  minimum_threshold: number;
  unit: string;
  is_below_threshold: boolean;
}
