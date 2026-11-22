/** Mirrors modules/gymkhana/api/serializers.py. */
export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export type ClubStatus = "open" | "confirmed";
export type Category = "technical" | "sports" | "cultural";

export interface Leaders {
  coordinator?: number;
  co_coordinator?: number;
}

export interface Club {
  id: number;
  name: string;
  category: Category;
  description: string;
  status: ClubStatus;
  faculty_councillor_user_id: number;
  councillor_name: string;
  approved_at: string | null;
  created_at: string;
  leaders: Leaders;
  leader_names: { coordinator?: string; co_coordinator?: string };
  my_membership: ClubStatus | null;
}

export interface MyClubs {
  leading: Club[];
  member_of: Club[];
}

export interface ClubInput {
  name: string;
  category: string;
  description: string;
  coordinator_user_id: number;
  co_coordinator_user_id: number;
  faculty_councillor_user_id: number;
}

export interface Membership {
  id: number;
  club: number;
  club_name: string;
  user_id: number;
  applicant_name: string;
  description: string;
  status: ClubStatus;
  remarks: string;
  approved_at: string | null;
  created_at: string;
}

export interface ApprovalOutcome {
  id: number;
  outcome: "approved" | "refused";
  code: string;
  message: string;
}

export interface Booking {
  id: number;
  club: number;
  club_name: string;
  kind: "session" | "event";
  venue_name: string;
  date: string;
  start_time: string;
  end_time: string;
  description: string;
  poster_link: string;
  event_name: string;
  faculty_user_id: number | null;
  created_at: string;
}

export interface BookingInput {
  club_id: number;
  venue: string;
  date: string;
  start_time: string;
  end_time: string;
  description: string;
  poster_url: string;
  event_name?: string;
}

export interface Choice {
  id: number;
  label: string;
  votes?: number;
}

export interface Poll {
  id: number;
  club: number;
  club_name: string;
  title: string;
  description: string;
  expires_on: string;
  created_at: string;
  choices: Choice[];
  my_choice_id: number | null;
}

export interface Target {
  batch_year: number;
  discipline: string;
}

export interface ManagedPoll extends Omit<Poll, "my_choice_id"> {
  targets: Target[];
  total_votes: number;
}

export interface PollInput {
  club_id: number;
  title: string;
  description: string;
  expires_on: string;
  choices: string[];
  targets: Target[];
}

export interface BudgetRequest {
  id: number;
  club: number;
  club_name: string;
  purpose: string;
  description: string;
  amount: string;
  document_link: string;
  status: "open";
  submitted_by_user_id: number;
  created_at: string;
}

export interface BudgetInput {
  club_id: number;
  purpose: string;
  description: string;
  amount: string;
  document_url: string;
}

export interface EventReport {
  id: number;
  club: number;
  club_name: string;
  student_incharge_user_id: number;
  student_incharge_name: string;
  event_name: string;
  event_at: string;
  description: string;
  report_link: string;
  submitted_by_user_id: number;
  created_at: string;
}

export interface ReportInput {
  club_id: number;
  student_incharge_user_id: number;
  event_name: string;
  event_at: string;
  description: string;
  report_url: string;
}

export interface Person {
  user_id: number;
  username: string;
  display_name: string;
  kind: "student" | "faculty";
}
