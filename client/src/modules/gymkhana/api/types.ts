/** Types mirroring modules/gymkhana/api/serializers.py. */
export interface Page<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface LedClub {
  id: number;
  name: string;
  status: "open" | "confirmed";
  faculty_councillor_id: number;
}

export interface Access {
  permissions: string[];
  clubs_led: LedClub[];
}

export interface Person {
  user_id: number;
  username: string;
  display_name: string;
}

export type PersonKind = "student" | "faculty";
export type ClubCategory = "technical" | "sports" | "cultural";

export interface Club {
  id: number;
  name: string;
  category: ClubCategory;
  description: string;
  coordinator_id: number;
  coordinator_name: string;
  co_coordinator_id: number;
  co_coordinator_name: string;
  faculty_councillor_id: number;
  faculty_councillor_name: string;
  status: "open" | "confirmed";
  created_at: string;
  updated_at: string;
}

export interface NewClub {
  name: string;
  category: ClubCategory;
  description: string;
  coordinator_id: number;
  co_coordinator_id: number;
  faculty_councillor_id: number;
}

export interface Booking {
  id: number;
  club_id: number;
  club_name: string;
  booking_type: "session" | "event";
  venue: string;
  booking_date: string;
  start_time: string;
  end_time: string;
  name: string;
  description: string;
  poster_file: string | null;
  faculty_councillor_id: number | null;
  booked_by_id: number;
  created_at: string;
}

export interface Membership {
  id: number;
  club_id: number;
  club_name: string;
  student_id: number;
  student_name: string;
  description: string;
  status: "open" | "confirmed";
  remarks: string;
  applied_at: string;
  approved_at: string | null;
  approved_by_id: number | null;
}

export interface PollGroup {
  batch: string;
  branch: string;
}

export interface Poll {
  id: number;
  club_id: number;
  club_name: string;
  created_by_id: number;
  title: string;
  description: string;
  expires_at: string;
  status: "active" | "expired";
  created_at: string;
  choices: { id: number; choice_text: string; vote_count: number }[];
  target_groups: PollGroup[];
  has_voted: boolean;
}

export interface NewPoll {
  club_id: number;
  title: string;
  description: string;
  expires_at: string;
  choices: string[];
  target_groups: PollGroup[];
}

export interface PollOptions {
  batches: string[];
  branches: string[];
}

export interface Budget {
  id: number;
  club_id: number;
  club_name: string;
  submitted_by_id: number;
  amount: string;
  purpose: string;
  description: string;
  supporting_file: string | null;
  status: "open";
  submitted_at: string;
}

export interface EventReport {
  id: number;
  club_id: number;
  club_name: string;
  submitted_by_id: number;
  student_incharge_id: number;
  student_incharge_name: string;
  event_name: string;
  event_date: string;
  description: string;
  report_file: string | null;
  submitted_at: string;
}
