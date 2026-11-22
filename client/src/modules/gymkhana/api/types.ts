export type ClubCategory = "Technical" | "Sports" | "Cultural";
export type ClubStatus = "open" | "confirmed";

export interface ClubSummary {
  id: number;
  name: string;
  category: ClubCategory;
  status: string;
  coordinator_id: number;
  co_coordinator_id: number;
  faculty_councillor_id: number;
  created_at: string;
}

export interface ClubDetail extends ClubSummary {
  description: string;
  updated_at: string;
  leadership_history: ClubLeadershipHistory[];
}

export interface ClubLeadershipHistory {
  id: number;
  coordinator_id: number;
  co_coordinator_id: number;
  effective_from: string;
  effective_to: string | null;
  changed_by_user_id: number;
}

export interface ClubCreateInput {
  name: string;
  category: ClubCategory;
  description: string;
  coordinator_id: number;
  co_coordinator_id: number;
  faculty_councillor_id: number;
}

export interface ClubLeadershipInput {
  new_coordinator_id: number;
  new_co_coordinator_id: number;
}

export interface Membership {
  id: number;
  club_id: number;
  club_name: string;
  student_id: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface MembershipApplyInput {
  club_id: number;
}

export interface MembershipApproveInput {
  remarks?: string;
}

export interface Booking {
  id: number;
  booking_type: string;
  club_id: number;
  club_name: string;
  venue: string;
  date: string;
  start_time: string;
  end_time: string;
  name: string;
  description: string;
  poster_url: string;
  poster_file_id: string | null;
  faculty_councillor_id: number | null;
  created_at: string;
}

export interface SessionBookingInput {
  club_id: number;
  venue: string;
  date: string;
  start_time: string;
  end_time: string;
  name?: string;
  description: string;
  poster_url?: string;
}

export interface EventBookingInput {
  club_id: number;
  faculty_councillor_id?: number | null;
  venue: string;
  date: string;
  start_time: string;
  end_time: string;
  name: string;
  description: string;
  poster_url?: string;
}

export interface PollChoice {
  id: number;
  text: string;
  tally: number;
}

export interface PollTarget {
  id: number;
  batch_year: number;
  discipline: string;
}

export interface PollSummary {
  id: number;
  club_id: number;
  club_name: string;
  title: string;
  description: string;
  expires_at: string;
  status: string;
  created_at: string;
}

export interface PollDetail extends PollSummary {
  choices: PollChoice[];
  targets: PollTarget[];
  has_voted: boolean;
  selected_choice_id: number | null;
  created_by_user_id: number;
}

export interface PollTargetInput {
  batch_year: number;
  discipline?: string;
}

export interface PollCreateInput {
  club_id: number;
  title: string;
  description: string;
  expires_at: string;
  choices: string[];
  targets: PollTargetInput[];
}

export interface PollVoteInput {
  choice_id: number;
}

export interface PollVoteResult {
  id: number;
  poll_id: number;
  choice_id: number;
  student_id: number;
  created_at: string;
}

export interface BudgetRequest {
  id: number;
  club_id: number;
  club_name: string;
  amount: string;
  purpose: string;
  description: string;
  supporting_file_url: string;
  supporting_file_id: string | null;
  status: string;
  submitted_by_user_id: number;
  created_at: string;
}

export interface BudgetRequestInput {
  amount: string;
  purpose: string;
  description: string;
  supporting_file_url: string;
}

export interface EventReport {
  id: number;
  club_id: number;
  club_name: string;
  student_incharge_id: number;
  event_name: string;
  event_date: string;
  event_time: string;
  description: string;
  report_file_url: string;
  report_file_id: string | null;
  submitted_by_user_id: number;
  created_at: string;
}

export interface EventReportInput {
  student_incharge_id: number;
  event_name: string;
  event_date: string;
  event_time: string;
  description: string;
  report_file_url: string;
}

export type BookingFilters = {
  date?: string;
  venue?: string;
  booking_type?: string;
  club_id?: number;
};
