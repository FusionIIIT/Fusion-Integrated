export interface Club {
  id: number;
  name: string;
  category: "Technical" | "Sports" | "Cultural";
  coordinator_user_id: number;
  co_coordinator_user_id: number;
  faculty_councillor_user_id: number;
  description: string;
  status: "open" | "confirmed";
  created_at: string;
}

export interface MembershipApplication {
  id: number;
  club: number;
  club_name?: string;
  student_user_id: number;
  description: string;
  status: "open" | "confirmed";
  remarks: string;
  created_at: string;
}

export interface PollChoice {
  id: number;
  text: string;
  vote_count: number;
}

export interface Poll {
  id: number;
  club: number;
  title: string;
  description: string;
  expires_at: string;
  choices: PollChoice[];
  has_voted: boolean;
}

export interface Activity {
  id: number;
  venue: string;
  date: string;
  start_time: string;
  end_time: string;
  description: string;
  poster_url: string;
}

export interface ClubEvent {
  id: number;
  name: string;
  venue: string;
  date: string;
  start_time: string;
  end_time: string;
  description: string;
  faculty_user_id: number;
  poster_url: string;
}

export interface BudgetRequest {
  id: number;
  amount: string;
  purpose: string;
  description: string;
  download_url: string;
  status: "open";
  created_at: string;
}

export interface EventReport {
  id: number;
  club_name?: string;
  student_incharge_user_id: number;
  event_name: string;
  event_at: string;
  description: string;
  download_url: string;
  created_at: string;
}

export interface DirectoryPerson {
  user_id: number;
  display_name: string;
  username: string;
  kind: "student" | "faculty";
  batch_year: number | null;
  discipline: string;
}

export interface TargetGroup {
  batch_year: number;
  discipline: string;
}
