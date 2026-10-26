import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { http } from '../../../lib/http';

export interface LeaveType {
  id: number;
  type: string;
  days_allowed: number;
  carry_forward: boolean;
  requires_substitute: boolean;
}

export interface LeaveBalance {
  id: number;
  employee: number;
  leave_type: number;
  balance: string;
  year: number;
}

export interface LeaveRequest {
  id: number;
  employee: number;
  leave_type: number;
  start_date: string;
  end_date: string;
  purpose: string;
  status: string;
  substitute: number | null;
  substitute_status: string;
  route: number[];
  step: number;
  operation: string;
  base_request: number | null;
  days: string;
  half_day: string;
  notes: string;
  actual_return_date: string | null;
  events: Array<{
    id: number;
    action: string;
    actor: number | null;
    created_at: string;
    details: Record<string, unknown>;
  }>;
}

export interface LeaveInput {
  leave_type: number;
  start_date: string;
  end_date: string;
  purpose: string;
  half_day?: string;
  substitute?: number | null;
  station_leave?: boolean;
  station_details?: string;
  medical_evidence?: string;
}

const fetchAll = async <T>(path: string): Promise<T[]> => {
  const results: T[] = [];
  const seen = new Set<string>();
  let next: string | null = path;

  while (next !== null) {
    if (seen.has(next)) {
      throw new Error('Repeated pagination URL');
    }
    seen.add(next);

    const { data }: { data: T[] | { results: T[]; next: string | null } } = await http.get<T[] | { results: T[], next: string | null }>(next);

    if (Array.isArray(data)) {
      results.push(...data);
      next = null;
    } else {
      results.push(...data.results);
      next = data.next;
    }
  }

  return results;
};
export const useLeaveRequests = () => {
  return useQuery({
    queryKey: ['leave-requests'],
    queryFn: async () => fetchAll<LeaveRequest>('/elm/requests/'),
    initialData: []
  });
};

export const useLeaveBalances = () => {
  return useQuery({
    queryKey: ['leave-balances'],
    queryFn: async () => fetchAll<LeaveBalance>('/elm/balances/'),
    initialData: []
  });
};

export const useLeaveTypes = () => {
  return useQuery({
    queryKey: ['leave-types'],
    queryFn: async () => fetchAll<LeaveType>('/elm/types/'),
    initialData: []
  });
};

export const useLeavePolicies = () => {
  return useQuery({
    queryKey: ['leave-policies'],
    queryFn: async () => fetchAll<Record<string, any>>('/elm/policies/'),
    initialData: []
  });
};
export const useCreateLeave = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: LeaveInput) => http.post('/elm/requests/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leave-requests'] });
      queryClient.invalidateQueries({ queryKey: ['leave-balances'] });
    }
  });
};

export const useLeaveAction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ request_id, action, payload }: { request_id: number; action: 'decide' | 'withdraw' | 'substitute-response' | 'renominate' | 'amend', payload?: Record<string, unknown> }) => {
      const res = await http.post(`/elm/requests/${request_id}/${action}/`, payload || {});
      return res;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leave-requests'] });
      queryClient.invalidateQueries({ queryKey: ['leave-balances'] });
    }
  });
};

export const useApproveLeave = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ request_id, status }: { request_id: number; status: 'APPROVED' | 'REJECTED' }) => {
      const res = await http.post(`/elm/requests/${request_id}/decide/`, {
        decision: status === 'APPROVED' ? 'APPROVE' : 'REJECT'
      });
      return res;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leave-requests'] });
      queryClient.invalidateQueries({ queryKey: ['leave-balances'] });
    }
  });
};
