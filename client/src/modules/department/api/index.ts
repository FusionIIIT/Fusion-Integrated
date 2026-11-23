import type { Notice, Slot, Lab, Proposal, Item, StockRequest, Feedback, ManagedAnnouncement, Announcement, Details, AcademicContext } from "./types";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../../../auth/AuthProvider";
import { http } from "../../../lib/http";

interface Page<T> {
  next: string | null;
  results: T[];
}

function useDepartmentFeed<T>(resource: string, refresh?: number) {
  const { session } = useAuth();
  const query = useInfiniteQuery({
    queryKey: ["department", resource, session?.user.id, session?.active_role],
    initialPageParam: null as string | null,
    queryFn: async ({ pageParam, signal }) => (await http.get<Page<T>>(`/department/${resource}`, {
      params: { cursor: pageParam }, signal,
    })).data,
    getNextPageParam: (page) => page.next
      ? new URL(page.next, window.location.origin).searchParams.get("cursor")
      : null,
    gcTime: 0,
    refetchInterval: refresh,
  });
  return { ...query, rows: query.data?.pages.flatMap((page) => page.results) ?? [] };
}

export function useDepartmentAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ path, data, method = "post" }: { path: string; data: unknown; method?: "post" | "put" }) =>
      http[method](`/department/${path}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["department"] }),
  });
}

function useDepartmentRecord<T>(resource: string, enabled = true) {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["department", resource, session?.user.id, session?.active_role],
    queryFn: async ({ signal }) => (await http.get<T>(`/department/${resource}`, { signal })).data,
    enabled,
    gcTime: 0,
  });
}

export function useNotices(refresh?: number) {
  return useDepartmentFeed<Notice>("notices", refresh);
}

export function useTimetable() {
  return useDepartmentFeed<Slot>("timetable");
}

export function useLabs() {
  return useDepartmentFeed<Lab>("labs");
}

export function useProposals() {
  return useDepartmentFeed<Proposal>("proposals");
}

export function useInventory() {
  return useDepartmentFeed<Item>("inventory");
}

export function useStockRequests() {
  return useDepartmentFeed<StockRequest>("stock-requests");
}

export function useFeedback() {
  return useDepartmentFeed<Feedback>("feedback");
}

export function useManagedAnnouncements() {
  return useDepartmentFeed<ManagedAnnouncement>("announcements/managed");
}

export function useAnnouncements() {
  return useDepartmentFeed<Announcement>("announcements");
}

export function useDetails() {
  return useDepartmentRecord<Details>("details");
}

export function useAcademicContext(enabled: boolean) {
  return useDepartmentRecord<AcademicContext>("academic-context", enabled);
}

export function useAccess() {
  return useDepartmentRecord<{ permissions: string[] }>("access");
}
