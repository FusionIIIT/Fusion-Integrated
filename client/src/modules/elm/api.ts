/** API client and React Query hooks for Employee Leave Management (ELM). */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http, errorMessage } from "../../lib/http";
import type {
  Holiday,
  LeaveBalance,
  LeaveRequest,
  LeaveRequestCreatePayload,
} from "./types";

const KEY = "elm";

export const elmKeys = {
  requests: (params?: unknown) => [KEY, "requests", params] as const,
  request: (id: number) => [KEY, "request", id] as const,
  balances: (year?: number) => [KEY, "balances", year] as const,
  inbox: () => [KEY, "inbox"] as const,
  holidays: (year?: number) => [KEY, "holidays", year] as const,
};

// --- Raw API Calls ---
export async function fetchLeaveRequests(params?: { status?: string; user_id?: number }): Promise<LeaveRequest[]> {
  const res = await http.get<LeaveRequest[]>("/elm/leave-requests/", { params });
  return res.data;
}

export async function fetchLeaveRequest(id: number): Promise<LeaveRequest> {
  const res = await http.get<LeaveRequest>(`/elm/leave-requests/${id}/`);
  return res.data;
}

export async function createLeaveRequest(payload: LeaveRequestCreatePayload): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>("/elm/leave-requests/", payload);
  return res.data;
}

export async function withdrawLeaveRequest(id: number, remarks: string = ""): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/elm/leave-requests/${id}/withdraw/`, { remarks });
  return res.data;
}

export async function respondSubstitute(id: number, action: "accept" | "decline", remarks: string = ""): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/elm/leave-requests/${id}/substitute-respond/`, { action, remarks });
  return res.data;
}

export async function nominateReplacementSubstitute(id: number, substitute_id: number, remarks: string = ""): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/elm/leave-requests/${id}/nominate-replacement-substitute/`, { substitute_id, remarks });
  return res.data;
}

export async function reviewUnitHead(
  id: number,
  decision: "approve" | "reject" | "recommended" | "not_recommended",
  remarks: string = ""
): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/elm/leave-requests/${id}/unit-head-review/`, { decision, remarks });
  return res.data;
}

export async function sanctionLeave(id: number, decision: "approve" | "reject", remarks: string = ""): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/elm/leave-requests/${id}/sanction/`, { decision, remarks });
  return res.data;
}

export async function requestCancellation(id: number, remarks: string): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/elm/leave-requests/${id}/request-cancellation/`, { remarks });
  return res.data;
}

export async function reviewCancellationUnitHead(
  id: number,
  decision: "approve" | "reject" | "recommended" | "not_recommended",
  remarks: string = ""
): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/elm/leave-requests/${id}/cancellation-unit-head-review/`, { decision, remarks });
  return res.data;
}

export async function sanctionCancellation(id: number, decision: "approve" | "reject", remarks: string = ""): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/elm/leave-requests/${id}/sanction-cancellation/`, { decision, remarks });
  return res.data;
}

export async function fetchLeaveBalances(year?: number): Promise<LeaveBalance[]> {
  const res = await http.get<LeaveBalance[]>("/elm/balances/", { params: year ? { year } : {} });
  return res.data;
}

export async function fetchPendingApprovals(): Promise<LeaveRequest[]> {
  const res = await http.get<LeaveRequest[]>("/elm/inbox/pending/");
  return res.data;
}

export async function fetchHolidays(year?: number): Promise<Holiday[]> {
  const res = await http.get<Holiday[]>("/elm/holidays/", { params: year ? { year } : {} });
  return res.data;
}

// --- React Query Hooks ---
export function useLeaveRequests(params?: { status?: string; user_id?: number }) {
  return useQuery({
    queryKey: elmKeys.requests(params),
    queryFn: () => fetchLeaveRequests(params),
  });
}

export function useLeaveRequest(id: number) {
  return useQuery({
    queryKey: elmKeys.request(id),
    queryFn: () => fetchLeaveRequest(id),
    enabled: Number.isInteger(id) && id > 0,
  });
}

export function useLeaveBalances(year?: number) {
  return useQuery({
    queryKey: elmKeys.balances(year),
    queryFn: () => fetchLeaveBalances(year),
  });
}

export function usePendingApprovals() {
  return useQuery({
    queryKey: elmKeys.inbox(),
    queryFn: () => fetchPendingApprovals(),
  });
}

export function useHolidays(year?: number) {
  return useQuery({
    queryKey: elmKeys.holidays(year),
    queryFn: () => fetchHolidays(year),
  });
}

export function useCreateLeaveRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createLeaveRequest,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useWithdrawLeaveRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, remarks }: { id: number; remarks?: string }) => withdrawLeaveRequest(id, remarks),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useRespondSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action, remarks }: { id: number; action: "accept" | "decline"; remarks?: string }) =>
      respondSubstitute(id, action, remarks),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useReviewUnitHead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      decision,
      remarks,
    }: {
      id: number;
      decision: "approve" | "reject" | "recommended" | "not_recommended";
      remarks?: string;
    }) => reviewUnitHead(id, decision, remarks),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useSanctionLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, decision, remarks }: { id: number; decision: "approve" | "reject"; remarks?: string }) =>
      sanctionLeave(id, decision, remarks),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export function useRequestCancellation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, remarks }: { id: number; remarks: string }) => requestCancellation(id, remarks),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}
