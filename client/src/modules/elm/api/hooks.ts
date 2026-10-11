// ELM API hooks
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { http } from '../../../lib/http';

// Leave Requests
export const useLeaveRequests = () => {
  return useQuery({
    queryKey: ['leave-requests'],
    queryFn: async () => {
      const { data } = await http.get('/elm/requests/');
      return data;
    }
  });
};

export const useApproveLeave = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ request_id, status }: { request_id: number; status: 'APPROVED' | 'REJECTED' }) => {
      await http.patch(`/elm/requests/${request_id}/`, { status });
      await queryClient.invalidateQueries({ queryKey: ['leave-requests'] });
    }
  });
};

// Leave Balances
export const useLeaveBalances = () => {
  return useQuery({
    queryKey: ['leave-balances'],
    queryFn: async () => {
      const { data } = await http.get('/elm/balances/');
      return data;
    }
  });
};

// Leave Types
export const useLeaveTypes = () => {
  return useQuery({
    queryKey: ['leave-types'],
    queryFn: async () => {
      const { data } = await http.get('/elm/types/');
      return data;
    }
  });
};

// Leave Policies
export const useLeavePolicies = () => {
  return useQuery({
    queryKey: ['leave-policies'],
    queryFn: async () => {
      const { data } = await http.get('/elm/policies/');
      return data;
    }
  });
};
