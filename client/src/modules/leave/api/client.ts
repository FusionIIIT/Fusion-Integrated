import axios from 'axios';

const BASE_URL = '/api/v1/leave';

interface LeaveApplication {
  id: number;
  employeeId: number;
  startDate: string;
  endDate: string;
  type: string;
  status: string;
  reason: string;
  createdAt: string;
  updatedAt: string;
}

interface LeaveBalance {
  totalLeaves: number;
  usedLeaves: number;
  remainingLeaves: number;
}

interface LeaveLedgerEntry {
  id: number;
  leaveApplicationId: number;
  transactionType: string;
  amount: number;
  createdAt: string;
  updatedAt: string;
}

interface SubstituteRequest {
  id: number;
  leaveApplicationId: number;
  substituteEmployeeId: number;
  status: string;
  reason: string;
  createdAt: string;
  updatedAt: string;
}

interface HolidayCalendar {
  id: number;
  date: string;
  description: string;
}

interface Payload {
  [key: string]: any;
}

const client = axios.create({
  baseURL: BASE_URL,
});

export const getMyLeaves = async (): Promise<LeaveApplication[]> => {
  const response = await client.get('/my-leaves');
  return response.data;
};

export const applyForLeave = async (payload: Payload): Promise<LeaveApplication> => {
  const response = await client.post('/apply', payload);
  return response.data;
};

export const withdrawLeave = async (
  id: number,
  reason: string
): Promise<LeaveApplication> => {
  const response = await client.put(`/withdraw/${id}`, { reason });
  return response.data;
};

export const requestCancellation = async (
  id: number,
  reason: string
): Promise<LeaveApplication> => {
  const response = await client.put(`/cancel/${id}`, { reason });
  return response.data;
};

export const requestExtension = async (
  id: number,
  payload: Payload
): Promise<LeaveApplication> => {
  const response = await client.put(`/extend/${id}`, payload);
  return response.data;
};

export const submitResumption = async (
  id: number,
  payload: Payload
): Promise<LeaveApplication> => {
  const response = await client.put(`/resume/${id}`, payload);
  return response.data;
};

export const getMyBalances = async (): Promise<LeaveBalance> => {
  const response = await client.get('/my-balances');
  return response.data;
};

export const getLedgerHistory = async (): Promise<LeaveLedgerEntry[]> => {
  const response = await client.get('/ledger-history');
  return response.data;
};

export const getMySubstituteRequests = async (): Promise<SubstituteRequest[]> => {
  const response = await client.get('/my-substitute-requests');
  return response.data;
};

export const respondSubstituteRequest = async (
  id: number,
  decision: 'accepted' | 'declined',
  remarks?: string
): Promise<SubstituteRequest> => {
  const payload: Payload = { decision };
  if (remarks) {
    payload.remarks = remarks;
  }
  const response = await client.put(`/respond-substitute-request/${id}`, payload);
  return response.data;
};

export const getPendingApprovals = async (): Promise<LeaveApplication[]> => {
  const response = await client.get('/pending-approvals');
  return response.data;
};

export const reviewUnitHead = async (
  id: number,
  recommended: boolean,
  remarks?: string
): Promise<LeaveApplication> => {
  const payload: Payload = { recommended };
  if (remarks) {
    payload.remarks = remarks;
  }
  const response = await client.put(`/review-unit-head/${id}`, payload);
  return response.data;
};

export const verifyEstablishment = async (
  id: number,
  remarks?: string
): Promise<LeaveApplication> => {
  const payload: Payload = {};
  if (remarks) {
    payload.remarks = remarks;
  }
  const response = await client.put(`/verify-establishment/${id}`, payload);
  return response.data;
};

export const sanctionLeave = async (
  id: number,
  decision: 'approved' | 'rejected',
  remarks?: string
): Promise<LeaveApplication> => {
  const payload: Payload = { decision };
  if (remarks) {
    payload.remarks = remarks;
  }
  const response = await client.put(`/sanction-leave/${id}`, payload);
  return response.data;
};

export const getHolidays = async (year?: number): Promise<HolidayCalendar[]> => {
  const params: URLSearchParams = new URLSearchParams();
  if (year) {
    params.append('year', year.toString());
  }
  const response = await client.get('/holidays', { params });
  return response.data;
};

export const recordOfflineLeave = async (payload: Payload): Promise<LeaveApplication> => {
  const response = await client.post('/offline-leave', payload);
  return response.data;
};