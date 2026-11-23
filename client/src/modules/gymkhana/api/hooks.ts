/** Data access for Gymkhana; every mutation refetches whatever it can affect. */
import {
  useInfiniteQuery, useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";

import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type {
  Access, Booking, Budget, Club, EventReport, Membership, NewClub, NewPoll, Page, Person,
  PersonKind, Poll, PollOptions,
} from "./types";

const KEY = "gymkhana";
type Params = Record<string, string | number | undefined>;

/** A cursor-paged list, flattened, with the next page fetched on request. */
function useList<T>(name: string, path: string, params: Params = {}, enabled = true) {
  const query = useInfiniteQuery({
    queryKey: [KEY, name, params],
    queryFn: async ({ pageParam }) =>
      (await http.get<Page<T>>(path, {
        params: { ...params, ...(pageParam ? { cursor: pageParam } : {}) },
      })).data,
    initialPageParam: "",
    getNextPageParam: (last) =>
      last.next ? new URL(last.next, window.location.origin).searchParams.get("cursor") : null,
    enabled,
    // Other people decide these rows, so opening a page never shows a cached answer.
    refetchOnMount: "always",
  });
  return {
    rows: query.data?.pages.flatMap((p) => p.results) ?? [],
    loading: enabled && query.isPending,
    error: query.error,
    hasMore: query.hasNextPage,
    loadMore: () => void query.fetchNextPage(),
    loadingMore: query.isFetchingNextPage,
  };
}

function useWrite<In, Out>(send: (body: In) => Promise<Out>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: send,
    // Not awaited: the refetch can unmount the form whose own onSuccess still has to run.
    onSuccess: () => { void qc.invalidateQueries({ queryKey: [KEY] }); },
  });
}

async function post<T>(path: string, body: unknown = {}): Promise<T> {
  return (await http.post<T>(path, body)).data;
}

/** Only the values given, so an untouched optional field is absent rather than "undefined". */
function multipart(body: Record<string, string | number | File | null>): FormData {
  const form = new FormData();
  for (const [key, value] of Object.entries(body)) {
    if (value === null) continue;
    form.append(key, value instanceof File ? value : String(value));
  }
  return form;
}

// -- What the acting role may do ------------------------------------------------
export function useAccess() {
  const query = useQuery({
    queryKey: [KEY, "access"],
    queryFn: async () => (await http.get<Access>("/gymkhana/access/")).data,
  });
  const permissions = new Set(query.data?.permissions ?? []);
  return {
    can: (code: string) => permissions.has(code),
    clubsLed: query.data?.clubs_led ?? [],
    loading: query.isPending,
    error: query.error,
  };
}

export function usePeople(q: string, kind: PersonKind) {
  return useQuery({
    queryKey: [KEY, "people", kind, q],
    queryFn: async () =>
      (await http.get<{ results: Person[] }>("/gymkhana/people/", { params: { q, kind } }))
        .data.results,
    enabled: q.length >= 3,
  });
}

// -- Clubs ------------------------------------------------------------------------
export const useClubs = () => useList<Club>("clubs", "/gymkhana/clubs/");

export const useCreateClub = () =>
  useWrite((body: NewClub) => post<Club>("/gymkhana/clubs/", body));

export const useConfirmClub = () =>
  useWrite((id: number) => post<Club>(`/gymkhana/clubs/${id}/confirm/`));

export const useChangeLeadership = () =>
  useWrite(({ id, ...body }: { id: number; coordinator_id: number; co_coordinator_id: number }) =>
    post<Club>(`/gymkhana/clubs/${id}/leadership/`, body));

// -- Bookings ---------------------------------------------------------------------
export const useBookings = (params: Params = {}) =>
  useList<Booking>("bookings", "/gymkhana/bookings/", params);

export function useVenues() {
  return useQuery({
    queryKey: [KEY, "venues"],
    queryFn: async () => (await http.get<{ venues: string[] }>("/gymkhana/venues/")).data.venues,
  });
}

export interface NewBooking {
  kind: "session" | "event";
  club_id: number;
  venue: string;
  booking_date: string;
  start_time: string;
  end_time: string;
  name: string;
  description: string;
  faculty_councillor_id: number | null;
  poster_file: File | null;
}

export const useBook = () =>
  useWrite(({ kind, ...body }: NewBooking) =>
    post<Booking>(`/gymkhana/bookings/${kind}/`, multipart({ ...body })));

// -- Memberships ------------------------------------------------------------------
export const useMemberships = (params: Params = {}, enabled = true) =>
  useList<Membership>("memberships", "/gymkhana/memberships/", params, enabled);

export const useApply = () =>
  useWrite((body: { club_id: number; description: string }) =>
    post<Membership>("/gymkhana/memberships/apply/", body));

/** Each application is decided on its own, so one refusal never undoes another (UC-GYM-005). */
export const useApproveMemberships = () =>
  useWrite(async ({ ids, remarks }: { ids: number[]; remarks: string }) => {
    const results = await Promise.allSettled(ids.map((id) =>
      post<Membership>(`/gymkhana/memberships/${id}/approve/`, { remarks })));
    const refused = results.find((r) => r.status === "rejected");
    return {
      approved: results.filter((r) => r.status === "fulfilled").length,
      refusal: refused?.status === "rejected" ? (refused.reason as unknown) : null,
    };
  });

// -- Polls ------------------------------------------------------------------------
export const usePolls = (params: Params = {}) =>
  useList<Poll>("polls", "/gymkhana/polls/", params);

export function usePollOptions(enabled: boolean) {
  return useQuery({
    queryKey: [KEY, "poll-options"],
    queryFn: async () => (await http.get<PollOptions>("/gymkhana/poll-options/")).data,
    enabled,
  });
}

export const useCreatePoll = () =>
  useWrite((body: NewPoll) => post<Poll>("/gymkhana/polls/", body));

export const useVote = () =>
  useWrite(({ id, choice_id }: { id: number; choice_id: number }) =>
    post<Poll>(`/gymkhana/polls/${id}/vote/`, { choice_id }));

// -- Budget requests and reports --------------------------------------------------
export const useBudgets = (params: Params = {}) =>
  useList<Budget>("budgets", "/gymkhana/budgets/", params);

export interface NewBudget {
  club_id: number;
  amount: string;
  purpose: string;
  description: string;
  supporting_file: File;
}

export const useSubmitBudget = () =>
  useWrite((body: NewBudget) => post<Budget>("/gymkhana/budgets/", multipart({ ...body })));

export const useReports = () => useList<EventReport>("reports", "/gymkhana/reports/");

export interface NewReport {
  club_id: number;
  student_incharge_id: number;
  event_name: string;
  event_date: string;
  description: string;
  report_file: File;
}

export const useSubmitReport = () =>
  useWrite((body: NewReport) => post<EventReport>("/gymkhana/reports/", multipart({ ...body })));

/** Fetched rather than navigated to, so a refusal stays inside the app. */
export function useDownload() {
  return useMutation({
    mutationFn: async (path: string) => {
      try {
        const res = await http.get<Blob>(path, { responseType: "blob" });
        saveBlob(res.data, filenameFromDisposition(
          res.headers["content-disposition"], "gymkhana-file"));
      } catch (e) {
        throw await readBlobError(e);
      }
    },
  });
}
