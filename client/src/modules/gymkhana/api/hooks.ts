/** Data access for the gymkhana module; every mutation invalidates the module's keys. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  ApprovalOutcome, Booking, BookingInput, BudgetInput, BudgetRequest, Club, ClubInput,
  EventReport, Leaders, ManagedPoll, Membership, MyClubs, Page, Person, Poll, PollInput,
  ReportInput,
} from "./types";

const KEY = "gymkhana";

export const keys = {
  clubs: (f?: unknown) => [KEY, "clubs", f] as const,
  myClubs: () => [KEY, "my-clubs"] as const,
  memberships: (f?: unknown) => [KEY, "memberships", f] as const,
  venues: () => [KEY, "venues"] as const,
  bookings: (f?: unknown) => [KEY, "bookings", f] as const,
  polls: () => [KEY, "polls"] as const,
  managedPolls: (club?: number) => [KEY, "managed-polls", club] as const,
  budget: (club?: number) => [KEY, "budget", club] as const,
  reports: (club?: number) => [KEY, "reports", club] as const,
  report: (id: number) => [KEY, "report", id] as const,
  people: (q: string, kind: string) => [KEY, "people", q, kind] as const,
};

function useInvalidate() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

async function get<T>(path: string, params?: object): Promise<T> {
  return (await http.get<T>(`/gymkhana/${path}`, { params })).data;
}

function useWrite<I, O>(path: (input: I) => string, body: (input: I) => unknown = (i) => i) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (input: I) =>
      (await http.post<O>(`/gymkhana/${path(input)}`, body(input))).data,
    onSuccess: invalidate,
  });
}

export function useClubs(filters?: { status?: string }) {
  return useQuery({ queryKey: keys.clubs(filters),
    queryFn: () => get<Page<Club>>("clubs", filters) });
}

export function useMyClubs() {
  return useQuery({ queryKey: keys.myClubs(), queryFn: () => get<MyClubs>("me/clubs") });
}

export function useCreateClub() {
  return useWrite<ClubInput, Club>(() => "clubs/create");
}

export function useApproveClub() {
  return useWrite<number, Club>((id) => `clubs/${id}/approve`, () => ({}));
}

export function useChangeLeadership() {
  return useWrite<{ clubId: number; coordinator_user_id: number;
    co_coordinator_user_id: number }, Leaders>(
    (i) => `clubs/${i.clubId}/leadership`,
    ({ coordinator_user_id, co_coordinator_user_id }) =>
      ({ coordinator_user_id, co_coordinator_user_id }));
}

export function useMemberships(filters?: { club?: number; status?: string }) {
  return useQuery({ queryKey: keys.memberships(filters),
    queryFn: () => get<Page<Membership>>("memberships", filters) });
}

export function useApply() {
  return useWrite<{ club_id: number; description: string }, Membership>(
    () => "memberships/apply");
}

export function useApproveMemberships() {
  return useWrite<{ ids: number[]; remarks: string }, ApprovalOutcome[]>(
    () => "memberships/approve");
}

export function useVenues(enabled = true) {
  return useQuery({ queryKey: keys.venues(), enabled,
    queryFn: () => get<{ venues: string[] }>("venues") });
}

export function useBookings() {
  return useQuery({ queryKey: keys.bookings(), queryFn: () => get<Page<Booking>>("bookings") });
}

export function useBook(kind: "session" | "event") {
  return useWrite<BookingInput, Booking>(() => (kind === "event" ? "events" : "sessions"));
}

export function useOpenPolls() {
  return useQuery({ queryKey: keys.polls(), queryFn: () => get<Page<Poll>>("polls") });
}

export function useManagedPolls(club?: number) {
  return useQuery({ queryKey: keys.managedPolls(club), enabled: club !== undefined,
    queryFn: () => get<Page<ManagedPoll>>("polls/managed", { club }) });
}

export function useCreatePoll() {
  return useWrite<PollInput, Poll>(() => "polls/create");
}

export function useVote() {
  return useWrite<{ pollId: number; choice_id: number }, { choice_id: number }>(
    (i) => `polls/${i.pollId}/votes`, ({ choice_id }) => ({ choice_id }));
}

export function useBudgetRequests(club?: number) {
  return useQuery({ queryKey: keys.budget(club), enabled: club !== undefined,
    queryFn: () => get<Page<BudgetRequest>>("budget-requests", { club }) });
}

export function useSubmitBudget() {
  return useWrite<BudgetInput, BudgetRequest>(() => "budget-requests/create");
}

export function useReports(club?: number) {
  return useQuery({ queryKey: keys.reports(club),
    queryFn: () => get<Page<EventReport>>("event-reports", club ? { club } : undefined) });
}

export function useReport(id: number | null) {
  return useQuery({ queryKey: keys.report(id ?? 0), enabled: id !== null,
    queryFn: () => get<EventReport>(`event-reports/${id}`) });
}

export function useSubmitReport() {
  return useWrite<ReportInput, EventReport>(() => "event-reports/create");
}

export function usePeople(q: string, kind: "student" | "faculty") {
  return useQuery({ queryKey: keys.people(q, kind), enabled: q.trim().length >= 2,
    queryFn: () => get<Person[]>("people", { q, kind }), staleTime: 30_000 });
}
