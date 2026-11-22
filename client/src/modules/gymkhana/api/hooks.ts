import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Activity,
  BudgetRequest,
  Club,
  ClubEvent,
  DirectoryPerson,
  EventReport,
  MembershipApplication,
  Poll,
} from "./types";

const root = "/gymkhana";

function useResults<T>(key: unknown[], path: string, enabled = true) {
  return useQuery({
    queryKey: key,
    queryFn: async () => (await http.get<{ results: T[] }>(path)).data.results,
    enabled,
  });
}

export const useClubs = () => useResults<Club>(["gymkhana", "clubs"], `${root}/clubs`);
export const useVenues = () =>
  useResults<string>(["gymkhana", "venues"], `${root}/venues`);
export const useMine = (enabled = true) =>
  useResults<MembershipApplication>(
    ["gymkhana", "memberships", "mine"], `${root}/memberships/mine`,
    enabled,
  );
export const useClubApplications = (clubId: number | null) =>
  useResults<MembershipApplication>(
    ["gymkhana", "memberships", clubId],
    `${root}/clubs/${clubId}/memberships`,
    clubId !== null,
  );
export const usePolls = (enabled = true) =>
  useResults<Poll>(["gymkhana", "polls"], `${root}/polls`, enabled);
export const useAssignedReports = (enabled = true) =>
  useResults<EventReport>(
    ["gymkhana", "reports", "assigned"], `${root}/reports/assigned`,
    enabled,
  );

export function usePeople(kind: "student" | "faculty", query: string) {
  return useQuery({
    queryKey: ["gymkhana", "people", kind, query],
    queryFn: async () => (await http.get<{ results: DirectoryPerson[] }>(
      `${root}/people`, { params: { kind, q: query } },
    )).data.results,
    enabled: query.trim().length >= 2,
  });
}

export function useClubSessions(clubId: number | null) {
  return useResults<Activity>(
    ["gymkhana", "sessions", clubId],
    `${root}/clubs/${clubId}/sessions`,
    clubId !== null,
  );
}

export function useClubEvents(clubId: number | null) {
  return useResults<ClubEvent>(
    ["gymkhana", "events", clubId],
    `${root}/clubs/${clubId}/events`,
    clubId !== null,
  );
}

export function useBudgets(clubId: number | null) {
  return useResults<BudgetRequest>(
    ["gymkhana", "budgets", clubId],
    `${root}/clubs/${clubId}/budgets`,
    clubId !== null,
  );
}

export function useClubReports(clubId: number | null) {
  return useResults<EventReport>(
    ["gymkhana", "reports", clubId],
    `${root}/clubs/${clubId}/reports`,
    clubId !== null,
  );
}

function useWrite<TData, TResult = unknown>(
  mutationFn: (data: TData) => Promise<TResult>,
  invalidate: unknown[][],
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: async () => {
      await Promise.all(invalidate.map((queryKey) =>
        queryClient.invalidateQueries({ queryKey })));
    },
  });
}

export const useCreateClub = () =>
  useWrite((data: FormData) => http.post(`${root}/clubs`, data), [
    ["gymkhana", "clubs"],
  ]);
export const useApproveClub = () =>
  useWrite((id: number) => http.post(`${root}/clubs/${id}/approve`), [
    ["gymkhana", "clubs"],
  ]);
export const useChangeLeadership = () =>
  useWrite(({ id, data }: { id: number; data: object }) =>
    http.post(`${root}/clubs/${id}/leadership`, data), [["gymkhana", "clubs"]]);
export const useApply = () =>
  useWrite(({ id, data }: { id: number; data: object }) =>
    http.post(`${root}/clubs/${id}/memberships`, data), [
    ["gymkhana", "memberships"],
  ]);
export const useApproveMembership = () =>
  useWrite(({ clubId, applicationId, remarks }: {
    clubId: number; applicationId: number; remarks: string;
  }) => http.post(
    `${root}/clubs/${clubId}/memberships/${applicationId}/approve`, { remarks },
  ), [["gymkhana", "memberships"]]);
export const useCreatePoll = () =>
  useWrite((data: object) => http.post(`${root}/polls`, data), [
    ["gymkhana", "polls"],
  ]);
export const useVote = () =>
  useWrite(({ pollId, choiceId }: { pollId: number; choiceId: number }) =>
    http.post(`${root}/polls/${pollId}/vote`, { choice_id: choiceId }), [
    ["gymkhana", "polls"],
  ]);
export const useCreateSession = () =>
  useWrite(({ clubId, data }: { clubId: number; data: FormData }) =>
    http.post(`${root}/clubs/${clubId}/sessions`, data), [
    ["gymkhana", "sessions"],
  ]);
export const useCreateEvent = () =>
  useWrite(({ clubId, data }: { clubId: number; data: FormData }) =>
    http.post(`${root}/clubs/${clubId}/events`, data), [
    ["gymkhana", "events"],
  ]);
export const useCreateBudget = () =>
  useWrite(({ clubId, data }: { clubId: number; data: FormData }) =>
    http.post(`${root}/clubs/${clubId}/budgets`, data), [
    ["gymkhana", "budgets"],
  ]);
export const useCreateReport = () =>
  useWrite(({ clubId, data }: { clubId: number; data: FormData }) =>
    http.post(`${root}/clubs/${clubId}/reports`, data), [
    ["gymkhana", "reports"],
  ]);
