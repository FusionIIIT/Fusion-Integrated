import type { LeaveApplication } from '../models';

export interface LeaveRequest {
  category: string;
  start_date: string;
  end_date: string;
  purpose?: string;
  substitute_user_id?: number;
}

export interface LeaveResponse extends LeaveApplication {}

export type LeaveCategory = 'CL' | 'RH' | 'SCL' | 'EL' | 'COL' | 'VL';

export interface Policy {
  CL_DAYS: number;
  RH_DAYS: number;
  SCL_MAX_DAYS: number;
  EL_DAYS: number;
  COL_DAYS: number;
  VL_DAYS: number;
  VL_TO_EL_RATIO: number;
}

export interface Calendar {
  year: number;
  holidays: Date[];
  restricted_holidays: Date[];
  is_effective: boolean;
}

export interface Notification {
  id: number;
  task_type: string;
  assigned_to_user_id: number;
  status: string;
  reminder_threshold_seconds: number;
  escalation_threshold_seconds: number;
  last_reminder_sent_at?: string;
  last_escalation_sent_at?: string;
}