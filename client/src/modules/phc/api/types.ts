export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface DoctorSchedule {
  id: number;
  doctor_name: string;
  specialization: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  published: boolean;
  is_present: boolean;
}

export interface Prescription {
  id: number;
  medicine: string;
  dosage: number;
  duration_days: number;
  notes: string;
}

export interface Visit {
  id: number;
  patient_id: number;
  schedule: number | null;
  visit_date: string;
  complaint: string;
  diagnosis: string;
  recorded_by: number;
  prescriptions: Prescription[];
}
