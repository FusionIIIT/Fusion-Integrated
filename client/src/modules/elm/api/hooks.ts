import { useQuery, useMutation } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import { LeaveRequest, Balance } from "./types";

const fetchBalance = async (): Promise<Balance[]> => {
  const response = await http.get<Balance[]>("/leave-requests/balance/");
  return response.data;
};

const fetchLeaveRequests = async (): Promise<LeaveRequest[]> => {
  const response = await http.get<LeaveRequest[]>("/leave-requests/");
  return response.data;
};

const applyLeaveRequest = async (data: { category: string; amount: number }) => {
  await http.post("/leave-requests/", data);
};

const withdrawLeaveRequest = async (id: number) => {
  await http.post(`/leave-requests/${id}/withdraw`);
};

export const useBalance = () => useQuery<Balance[], Error>(["balance"], fetchBalance);
export const useLeaveRequests = () => useQuery<LeaveRequest[], Error>(["leave-requests"], fetchLeaveRequests);
export const useApplyLeaveRequest = () => useMutation<void, Error, { category: string; amount: number }>(applyLeaveRequest);
export const useWithdrawLeaveRequest = () => useMutation<void, Error, number>(withdrawLeaveRequest);
