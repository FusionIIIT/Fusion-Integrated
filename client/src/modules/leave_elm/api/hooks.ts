import { useQuery, useMutation } from '@tanstack/react-query';
import { http } from '../../../lib/http';
import type { LeaveRequest } from './types';

const BASE = '/leave';

export function useMyLeave() {
  return useQuery({
    queryKey: ['leave', 'mine'],
    queryFn: () => http.get(`${BASE}/mine`),
  });
}

export function useApplyLeave(_data: Partial<LeaveRequest>) {
  return useMutation({
    mutationFn: (d: LeaveRequest) => http.post(`${BASE}/apply`, d),
  });
}

export function useLeaveDetails(id: number) {
  return useQuery({
    queryKey: ['leave', 'detail', id],
    queryFn: () => http.get(`${BASE}/${id}`),
    enabled: !!id,
  });
}

export function useWithdrawLeave(id: number) {
  return useMutation({
    mutationFn: (d: LeaveRequest) => http.post(`${BASE}/${id}/withdraw`, d),
  });
}

export function useCancelLeave(id: number) {
  return useMutation({
    mutationFn: () => http.post(`${BASE}/${id}/cancel`),
  });
}

export function useExtendLeave(id: number) {
  return useMutation({
    mutationFn: (d: { additional_days: number }) => 
      http.post(`${BASE}/${id}/extend`, d),
  });
}

export function useResumption(id: number) {
  return useMutation({
    mutationFn: (d: { actual_date: string }) => 
      http.post(`${BASE}/${id}/resumption`, d),
  });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: ['leave', 'balances'],
    queryFn: () => http.get(`${BASE}/balances`),
  });
}

export function useLeaveHistory() {
  return useQuery({
    queryKey: ['leave', 'history'],
    queryFn: () => http.get(`${BASE}/history`),
  });
}

export function useLeaveQueue(userId: number) {
  return useQuery({
    queryKey: ['leave', 'queue', userId],
    queryFn: () => http.get(`${BASE}/queue`),
  });
}

export function useSubstituteAccept(id: number) {
  return useMutation({
    mutationFn: () => http.post(`${BASE}/${id}/substitute/accept`),
  });
}

export function useSubstituteDecline(id: number) {
  return useMutation({
    mutationFn: (d: { new_substitute_user_id?: number }) => 
      http.post(`${BASE}/${id}/substitute/decline`, d),
  });
}

export function useReviewLeave(id: number) {
  return useMutation({
    mutationFn: (d: { decision: string }) => 
      http.post(`${BASE}/${id}/review`, d),
  });
}

export function usePolicy() {
  return useQuery({
    queryKey: ['leave', 'policy'],
    queryFn: () => http.get(`${BASE}/policy`),
  });
}

export function useCalendar() {
  return useQuery({
    queryKey: ['leave', 'calendar'],
    queryFn: () => http.get(`${BASE}/calendar`),
  });
}

export function useNotifications(userId: number) {
  return useQuery({
    queryKey: ['leave', 'notifications', userId],
    queryFn: () => http.get(`${BASE}/notifications`),
  });
}

export function useOfflineRecord() {
  return useMutation({
    mutationFn: (d: { category: string; start_date: string; end_date: string; reference_number?: string; evidence?: string }) => 
      http.post(`${BASE}/offline-record`, d),
  });
}