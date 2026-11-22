import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";

import type {
  Booking,
  BookingFilters,
  BudgetRequest,
  BudgetRequestInput,
  ClubCreateInput,
  ClubDetail,
  ClubLeadershipInput,
  ClubSummary,
  EventBookingInput,
  EventReport,
  EventReportInput,
  Membership,
  MembershipApplyInput,
  MembershipApproveInput,
  PollCreateInput,
  PollDetail,
  PollSummary,
  PollVoteInput,
  PollVoteResult,
  SessionBookingInput,
} from "./types";

const BASE = "/gymkhana";

export const gymkhanaKeys = {
  all: ["gymkhana"] as const,
  clubs: () => [...gymkhanaKeys.all, "clubs"] as const,
  club: (id: number) => [...gymkhanaKeys.clubs(), id] as const,
  memberships: () => [...gymkhanaKeys.all, "memberships"] as const,
  clubMemberships: (id: number, status?: string) =>
    [...gymkhanaKeys.memberships(), id, status] as const,
  bookings: (filters?: BookingFilters) =>
    [...gymkhanaKeys.all, "bookings", filters] as const,
  polls: () => [...gymkhanaKeys.all, "polls"] as const,
  poll: (id: number) => [...gymkhanaKeys.polls(), id] as const,
  budgets: (id: number) => [...gymkhanaKeys.all, "budgets", id] as const,
  reports: (id: number) => [...gymkhanaKeys.all, "reports", id] as const,
  report: (id: number) => [...gymkhanaKeys.all, "report", id] as const,
};

function invalidateGymkhana(qc: ReturnType<typeof useQueryClient>) {
  return qc.invalidateQueries({ queryKey: gymkhanaKeys.all });
}

export function useClubs() {
  return useQuery({
    queryKey: gymkhanaKeys.clubs(),
    queryFn: async () =>
      (await http.get<ClubSummary[]>(`${BASE}/clubs`)).data,
  });
}

export function useClub(id: number) {
  return useQuery({
    queryKey: gymkhanaKeys.club(id),
    queryFn: async () =>
      (await http.get<ClubDetail>(`${BASE}/clubs/${id}`)).data,
    enabled: id > 0,
  });
}

export function useCreateClub() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ClubCreateInput) =>
      (await http.post<ClubDetail>(`${BASE}/clubs`, body)).data,
    onSuccess: () => invalidateGymkhana(qc),
  });
}

export function useApproveClub() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<ClubDetail>(`${BASE}/clubs/${id}/approve`)).data,
    onSuccess: () => invalidateGymkhana(qc),
  });
}

export function useUpdateClubLeadership(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ClubLeadershipInput) =>
      (await http.post<ClubDetail>(
        `${BASE}/clubs/${id}/leadership`,
        body,
      )).data,
    onSuccess: () => invalidateGymkhana(qc),
  });
}

export function useMyMemberships() {
  return useQuery({
    queryKey: gymkhanaKeys.memberships(),
    queryFn: async () =>
      (await http.get<Membership[]>(`${BASE}/memberships`)).data,
  });
}

export function useApplyForMembership() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: MembershipApplyInput) =>
      (await http.post<Membership>(`${BASE}/memberships`, body)).data,
    onSuccess: () => invalidateGymkhana(qc),
  });
}

export function useClubMemberships(id: number, status?: string) {
  return useQuery({
    queryKey: gymkhanaKeys.clubMemberships(id, status),
    queryFn: async () =>
      (await http.get<Membership[]>(`${BASE}/clubs/${id}/memberships`, {
        params: status ? { status } : undefined,
      })).data,
    enabled: id > 0,
  });
}

export function useApproveMembership(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: MembershipApproveInput = {}) =>
      (await http.post<Membership>(
        `${BASE}/memberships/${id}/approve`,
        body,
      )).data,
    onSuccess: () => invalidateGymkhana(qc),
  });
}

export function useBookings(filters: BookingFilters = {}) {
  return useQuery({
    queryKey: gymkhanaKeys.bookings(filters),
    queryFn: async () =>
      (await http.get<Booking[]>(`${BASE}/bookings`, {
        params: filters,
      })).data,
  });
}

export function useBookSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: SessionBookingInput) =>
      (await http.post<Booking>(`${BASE}/sessions`, body)).data,
    onSuccess: () => invalidateGymkhana(qc),
  });
}

export function useBookEvent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: EventBookingInput) =>
      (await http.post<Booking>(`${BASE}/events`, body)).data,
    onSuccess: () => invalidateGymkhana(qc),
  });
}

export function usePolls() {
  return useQuery({
    queryKey: gymkhanaKeys.polls(),
    queryFn: async () =>
      (await http.get<PollSummary[]>(`${BASE}/polls`)).data,
  });
}

export function usePoll(id: number) {
  return useQuery({
    queryKey: gymkhanaKeys.poll(id),
    queryFn: async () =>
      (await http.get<PollDetail>(`${BASE}/polls/${id}`)).data,
    enabled: id > 0,
  });
}

export function useCreatePoll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PollCreateInput) =>
      (await http.post<PollDetail>(`${BASE}/polls`, body)).data,
    onSuccess: () => invalidateGymkhana(qc),
  });
}

export function useVotePoll(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PollVoteInput) =>
      (await http.post<PollVoteResult>(
        `${BASE}/polls/${id}/vote`,
        body,
      )).data,
    onSuccess: () => invalidateGymkhana(qc),
  });
}

export function useClubBudgets(id: number) {
  return useQuery({
    queryKey: gymkhanaKeys.budgets(id),
    queryFn: async () =>
      (await http.get<BudgetRequest[]>(`${BASE}/clubs/${id}/budgets`)).data,
    enabled: id > 0,
  });
}

export function useSubmitBudget(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: BudgetRequestInput) =>
      (await http.post<BudgetRequest>(
        `${BASE}/clubs/${id}/budgets`,
        body,
      )).data,
    onSuccess: () => invalidateGymkhana(qc),
  });
}

export function useClubReports(id: number) {
  return useQuery({
    queryKey: gymkhanaKeys.reports(id),
    queryFn: async () =>
      (await http.get<EventReport[]>(`${BASE}/clubs/${id}/reports`)).data,
    enabled: id > 0,
  });
}

export function useSubmitEventReport(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: EventReportInput) =>
      (await http.post<EventReport>(
        `${BASE}/clubs/${id}/reports`,
        body,
      )).data,
    onSuccess: () => invalidateGymkhana(qc),
  });
}

export function useEventReport(id: number) {
  return useQuery({
    queryKey: gymkhanaKeys.report(id),
    queryFn: async () =>
      (await http.get<EventReport>(`${BASE}/reports/${id}`)).data,
    enabled: id > 0,
  });
}
