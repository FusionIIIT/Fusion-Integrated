import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";

export interface LeaveType {
  id: number;
  name: string;
  description: string;
}

export interface LeaveRequest {
  id: number;
  leave_type: number;
  start_date: string;
  end_date: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CreateLeaveRequestInput {
  leave_type: number;
  start_date: string;
  end_date: string;
}

interface Page<T> {
  results: T[];
}

function listFrom<T>(data: T[] | Page<T>): T[] {
  return Array.isArray(data) ? data : data.results;
}

export function useLeaveTypes() {
  return useQuery({
    queryKey: ["leave", "types"],
    queryFn: async () => {
      const response = await http.get<LeaveType[] | Page<LeaveType>>(
        "/leave/types",
      );
      return listFrom(response.data);
    },
  });
}

export function useLeaveRequests() {
  return useQuery({
    queryKey: ["leave", "requests"],
    queryFn: async () => {
      const response = await http.get<
        LeaveRequest[] | Page<LeaveRequest>
      >("/leave/requests");
      return listFrom(response.data);
    },
  });
}

export function useCreateLeaveRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: CreateLeaveRequestInput) => {
      const response = await http.post<LeaveRequest>(
        "/leave/requests",
        input,
      );
      return response.data;
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["leave"] }),
  });
}
