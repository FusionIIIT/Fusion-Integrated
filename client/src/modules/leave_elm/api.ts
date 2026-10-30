import type { LeaveApplication, LeaveBalance, LeaveTask, LeaveHistory, LeaveNotification } from "./types";
export type { LeaveApplication, LeaveBalance, LeaveTask, LeaveHistory, LeaveNotification } from "./types";


import { http } from '../../lib/http';




export interface Configuration {
  policy?: Record<string, unknown>[];
  calendar?: Record<string, unknown>[];
}

export interface NewApplication {
  leave_type: string | number;
  start_date: string;
  end_date: string;
  purpose: string;
  station_leave_required?: boolean;
  address_during_leave?: string;
  contact_number?: string;
  academic_substitute_user_id?: number | null;
  admin_substitute_user_id?: number | null;
  attachment_reference?: string;
  remarks?: string;
}

export async function listApplications(): Promise<LeaveApplication[]> {
  const response = await http.get('/leave/applications');
  return response.data as LeaveApplication[];
}

export async function listBalances(): Promise<LeaveBalance[]> {
  const response = await http.get('/leave/balances');
  return response.data as LeaveBalance[];
}

export async function listTasks(): Promise<LeaveTask[]> {
  const response = await http.get('/leave/tasks');
  return response.data as LeaveTask[];
}

export async function submitApplication(data: NewApplication): Promise<void> {
  await http.post('/leave/applications', data);
}

export async function applicationAction(id: number, action: string, data: { [key: string]: any } = {}): Promise<void> {
  await http.post(`/leave/applications/${id}/action`, { action, ...data });
}

export async function getConfiguration(): Promise<Configuration> {
  const response = await http.get('/leave/configuration');
  return response.data as Configuration;
}

export async function saveConfiguration(data: Configuration): Promise<void> {
  await http.post('/leave/configuration', data);
}

export async function getRecords(): Promise<{ history?: LeaveHistory[], notifications?: LeaveNotification[] }> {
  const response = await http.get('/leave/records');
  return response.data as { history?: LeaveHistory[], notifications?: LeaveNotification[] };
}

export async function listNotifications(): Promise<LeaveNotification[]> {
  const response = await http.get('/leave/notifications');
  return response.data as LeaveNotification[];
}

export async function adjustBalanceRecord(payload: Record<string, unknown>): Promise<void> {
  await http.post('/leave/records', payload);
}
