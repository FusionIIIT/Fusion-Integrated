import { http } from '../lib/http';

export async function createLeaveRequest(request: any) {
  return await http.post('/placement/leave-requests', request);
}

export async function getLeaveRequests() {
  return await http.get('/placement/leave-requests');
}