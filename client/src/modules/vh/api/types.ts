/** TypeScript types for Visitors Hostel (VH) module. */

export type VisitorCategoryCode = "A" | "B" | "C" | "D";

export interface VisitorCategory {
  id: number;
  code: VisitorCategoryCode;
  name: string;
  description: string;
}

export type RoomType = "SUITE" | "NON_SUITE";
export type OccupancyType = "SINGLE" | "DOUBLE";
export type RoomStatus = "AVAILABLE" | "OCCUPIED" | "MAINTENANCE";

export interface Room {
  id: number;
  room_number: string;
  room_type: RoomType;
  occupancy_type: OccupancyType;
  floor: number;
  status: RoomStatus;
  created_at: string;
}

export interface Tariff {
  id: number;
  category: number;
  category_code: VisitorCategoryCode;
  room_type: RoomType;
  occupancy_type: OccupancyType;
  rate_per_day: string;
  effective_from: string;
}

export type BillingResponsibility = "VISITOR" | "INDENTER" | "INSTITUTE" | "PROJECT";

export type BookingStatus =
  | "PENDING"
  | "FORWARDED"
  | "APPROVED"
  | "REJECTED"
  | "ROOM_ALLOTTED"
  | "CHECKED_IN"
  | "CHECKED_OUT"
  | "CANCELLATION_REQUESTED"
  | "CANCELLED";

export interface RoomAllotment {
  id: number;
  booking: number;
  room: number;
  room_number: string;
  room_type: RoomType;
  allotted_at: string;
  check_in_time: string | null;
  check_out_time: string | null;
  is_no_show: boolean;
  is_overstay: boolean;
}

export interface Bill {
  id: number;
  booking: number;
  booking_reference: string;
  room_charges: string;
  meal_charges: string;
  cancellation_charges: string;
  total_amount: string;
  payment_mode: string;
  is_settled: boolean;
  settled_at: string | null;
  is_finalized: boolean;
  guest_verification_notes: string;
}

export interface BookingModification {
  id: number;
  booking: number;
  booking_reference: string;
  requested_by_user_id: number;
  new_check_in_date: string | null;
  new_check_out_date: string | null;
  new_number_of_rooms: number | null;
  new_number_of_occupants: number | null;
  reason: string;
  status: "PENDING" | "CONFIRMED" | "REJECTED";
  confirmed_by_user_id: number | null;
  remarks: string;
  created_at: string;
}

export interface Booking {
  id: number;
  booking_reference: string;
  indenter_id: number;
  indenter_type: string;
  is_offline: boolean;
  offline_booking_type: string;
  visitor_name: string;
  visitor_email: string;
  visitor_phone: string;
  visitor_address: string;
  visitor_category: number;
  category_code: string;
  visit_purpose: string;
  check_in_date: string;
  check_out_date: string;
  number_of_rooms: number;
  number_of_occupants: number;
  billing_responsibility: BillingResponsibility;
  status: BookingStatus;
  assigned_caretaker_id: number | null;
  assigned_incharge_id: number | null;
  caretaker_remarks: string;
  incharge_remarks: string;
  cancellation_reason: string;
  calculated_cancellation_charge: string;
  allotments: RoomAllotment[];
  bill?: Bill | null;
  modifications?: BookingModification[];
  created_at: string;
  updated_at: string;
}

export type MealType = "BREAKFAST" | "LUNCH" | "DINNER" | "FULL_DAY";
export type MealAddOn = "NONE" | "TEA" | "MILK";

export interface MealBooking {
  id: number;
  booking: number;
  date: string;
  meal_type: MealType;
  add_on: MealAddOn;
  number_of_persons: number;
  rate: string;
  total_amount: string;
  created_at: string;
}

export interface InventoryItem {
  id: number;
  name: string;
  category: "LINEN" | "UTENSILS" | "CONSUMABLES" | "OTHERS";
  current_quantity: number;
  minimum_threshold: number;
  is_below_threshold: boolean;
  created_at: string;
}

export interface InventoryReplenishment {
  id: number;
  item: number;
  item_name: string;
  quantity_requested: number;
  requested_by_user_id: number;
  status: "PENDING" | "APPROVED" | "REJECTED";
  remarks: string;
  created_at: string;
}

export interface PrintableBookingSlip {
  title: string;
  booking_reference: string;
  indenter_id: number;
  visitor_name: string;
  visitor_phone: string;
  visitor_email: string;
  category: string;
  visit_purpose: string;
  check_in_date: string;
  check_out_date: string;
  number_of_rooms: number;
  status: BookingStatus;
  allotted_rooms: string[];
  billing_responsibility: string;
  bill?: Bill | null;
  generated_at: string;
}

export interface InChargeReport {
  booking_summary: {
    total_bookings: number;
    by_status: Record<string, number>;
  };
  category_occupancy: {
    category_code: string;
    category_name: string;
    bookings_count: number;
    total_rooms_booked: number;
  }[];
  revenue_summary: {
    room_charges: string;
    meal_charges: string;
    cancellation_charges: string;
    total_revenue: string;
    total_settled: string;
    total_pending_settlement: string;
  };
  inventory_usage: {
    total_inventory_items: number;
    items_below_threshold: string[];
    replenishments_approved: number;
    replenishments_pending: number;
  };
}

export interface CaretakerReport {
  daily_occupancy: {
    date: string;
    checked_in_guests: number;
    occupied_rooms: number;
    available_rooms: number;
    maintenance_rooms: number;
  };
  upcoming_arrivals: {
    id: number;
    booking_reference: string;
    visitor_name: string;
    check_in_date: string;
    status: string;
    number_of_rooms: number;
  }[];
  upcoming_departures: {
    id: number;
    booking_reference: string;
    visitor_name: string;
    check_out_date: string;
    status: string;
  }[];
  pending_actions: {
    pending_review_count: number;
    pending_cancellation_confirmations_count: number;
    pending_cancellations: {
      id: number;
      booking_reference: string;
      visitor_name: string;
      calculated_cancellation_charge: string;
    }[];
  };
  no_show_logs: {
    booking_id: number;
    booking_reference: string;
    visitor_name: string;
    room_number: string;
    expected_check_in: string;
  }[];
  overstay_logs: {
    booking_id: number;
    booking_reference: string;
    visitor_name: string;
    room_number: string;
    expected_check_out: string;
  }[];
  unresolved_alerts: {
    id: number;
    alert_type: string;
    message: string;
    created_at: string;
  }[];
}

