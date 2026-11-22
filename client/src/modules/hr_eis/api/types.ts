/** Types for HR / Employee Information System (EIS) */

export interface WorkExperience {
  id: number;
  organization: string;
  position: string;
  start_date: string;
  end_date: string | null;
  description: string;
}

export interface EmployeeProfile {
  id: number;
  username: string;
  email: string;
  pf_number: string;
  designation: string;
  department: string;
  date_of_joining: string;
  about_me: string;
  experiences: WorkExperience[];
}

export interface CreateExperiencePayload {
  organization: string;
  position: string;
  start_date: string;
  end_date?: string | null;
  description?: string;
}
