import { http } from '../../../lib/http';

export interface LeaveType {
  id: number;
  code: string;
  name: string;
  description?: string;
}

export interface LeaveBalance {
  id: number;
  user: number;
  leave_type: number;
  balance: number;
  year: number;
}

export interface LeaveApplication {
  id?: number;
  leave_type: number;
  start_date: string;
  end_date: string;
  half_day: string;
  reason: string;
  is_station_leave: boolean;
  station_leave_address?: string;
  status?: string;
}

export const fetchLeaveTypes = async () => {
  const res = await http.get<LeaveType[]>('/api/leave/types/');
  return res.data;
};

export const fetchLeaveBalances = async () => {
  const res = await http.get<LeaveBalance[]>('/api/leave/balances/');
  return res.data;
};

export const fetchLeaveApplications = async () => {
  const res = await http.get<LeaveApplication[]>('/api/leave/');
  return res.data;
};

export const createLeaveApplication = async (data: LeaveApplication) => {
  const res = await http.post<LeaveApplication>('/api/leave/', data);
  return res.data;
};