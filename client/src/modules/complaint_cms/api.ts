import { http } from '../../lib/http';
import type * as T from './types';
export type * from './types';

export async function listComplaints(): Promise<T.Complaint[]> {
  const res = await http.get('/complaints/');
  return res.data;
}

export async function submitComplaint(payload: T.NewComplaint): Promise<void> {
  await http.post('/complaints/', payload);
}

export async function listTasks(complaintId: number): Promise<T.ComplaintTask[]> {
  const res = await http.get(`/complaints/${complaintId}/tasks`);
  return res.data;
}

export async function listNotifications(complaintId: number): Promise<T.ComplaintNotificationRecord[]> {
  const res = await http.get(`/complaints/${complaintId}/notifications`);
  return res.data;
}

export async function complaintAction(
  id: number,
  action: string,
  data?: Record<string, unknown>
): Promise<void> {
  await http.patch(`/complaints/${id}/action`, { action, ...data });
}

export async function getConfiguration(): Promise<T.ConfigurationResponse> {
  const res = await http.get('/configuration/');
  return res.data;
}

export async function saveConfiguration(payload: Record<string, unknown>): Promise<void> {
  await http.put('/configuration/', payload);
}

export async function getRecords(): Promise<T.RecordListView[]> {
  const res = await http.get('/records/');
  return res.data;
}
