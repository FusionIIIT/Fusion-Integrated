import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

const API_BASE = '/api/v1/mms';

export const useMessMenu = () =>
  useQuery({
    queryKey: ['mess-menu'],
    queryFn: async () => (await axios.get(`${API_BASE}/menu/`)).data,
  });

export const useStudentBills = () =>
  useQuery({
    queryKey: ['student-bills'],
    queryFn: async () => (await axios.get(`${API_BASE}/my-bills/`)).data,
  });

export const useMmsReports = (reportType: string) =>
  useQuery({
    queryKey: ['mms-reports', reportType],
    queryFn: async () => (await axios.get(`${API_BASE}/reports/${reportType}/`)).data,
  });

export const useSubmitRegistration = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { window_id: number }) => axios.post(`${API_BASE}/register/`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mms-reports'] }),
  });
};

export const useSubmitRebate = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { reason: string; explanation?: string; start_date: string; end_date: string }) =>
      axios.post(`${API_BASE}/rebate/`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mms-reports'] }),
  });
};

export const useReviewRequest = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ moduleType, id, decision }: { moduleType: string; id: number; decision: string }) =>
      axios.post(`${API_BASE}/review/${moduleType}/${id}/`, { decision }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mms-reports'] }),
  });
};