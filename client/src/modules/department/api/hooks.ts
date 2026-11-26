/** Data access for the department module.
 *
 *  Every mutation invalidates the keys it can affect; no manual cache surgery.
 *  Getting that subtly wrong shows up as an enabled "Apply" button on a
 *  posting the student already applied to.
 */
import {
  useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Announcement,
  Feedback,
  InventoryItem,
  Page,
  StockRequest,
  TimetableSlot,
} from "./types";

const KEY = "department";

export const keys = {
  announcements: () => [KEY, "announcements"] as const,
  publishAnnouncement: () => [KEY, "publish-announcement"] as const,
  inventory: () => [KEY, "inventory"] as const,
  stockRequests: () => [KEY, "stock-requests"] as const,
  createStockRequest: (f?: unknown) => [KEY, "create-stock-request", f] as const,
  stockRequest: (id: number) => [KEY, "stock-requests", id] as const,
  decideStockRequest: (id: number) => [KEY, "stock-requests", id, "decide"] as const,
  issueStockRequest: (id: number) => [KEY, "stock-requests", id, "issue"] as const,
  feedback: () => [KEY, "feedback"] as const,
  submitFeedback: (f?: unknown) => [KEY, "submit-feedback", f] as const,
  disposeFeedback: (id: number) => [KEY, "feedback", id, "dispose"] as const,
  reviewFeedback: (id: number) => [KEY, "feedback", id, "review"] as const,
  timetable: () => [KEY, "timetable"] as const,
};

/** Coarse on purpose — these pages are small, and correctness beats shaving
 *  a refetch. */
function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Announcements -------------------------------------------------------------
export function useAnnouncements() {
  return useQuery({
    queryKey: keys.announcements(),
    queryFn: async () =>
      (await http.get<Page<Announcement>>("/department/announcements")).data,
    staleTime: 30_000,
  });
}

export function usePublishAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<Announcement>("/department/announcements", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Inventory ------------------------------------------------------------------
export function useInventory() {
  return useQuery({
    queryKey: keys.inventory(),
    queryFn: async () =>
      (await http.get<Page<InventoryItem>>("/department/inventory")).data,
    staleTime: 30_000,
  });
}

// -- Stock Requests ------------------------------------------------------------
export function useStockRequests() {
  return useQuery({
    queryKey: keys.stockRequests(),
    queryFn: async () =>
      (await http.get<Page<StockRequest>>("/department/stock-requests")).data,
    staleTime: 30_000,
  });
}

export function useCreateStockRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<StockRequest>("/department/stock-requests", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useStockRequest(id: number) {
  return useQuery({
    queryKey: keys.stockRequest(id),
    queryFn: async () =>
      (await http.get<StockRequest>(`/department/stock-requests/${id}`)).data,
    enabled: !!id,
  });
}

export function useDecideStockRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, outcome }: { id: number; outcome: "approved" | "rejected" }) =>
      (await http.post<StockRequest>(
        `/department/stock-requests/${id}/decide`,
        { outcome })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useIssueStockRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, quantity }: { id: number; quantity: number }) =>
      (await http.post<StockRequest>(
        `/department/stock-requests/${id}/issue`,
        { quantity })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Feedback ------------------------------------------------------------------
export function useFeedback() {
  return useQuery({
    queryKey: keys.feedback(),
    queryFn: async () =>
      (await http.get<Page<Feedback>>("/department/feedback")).data,
    staleTime: 30_000,
  });
}

export function useSubmitFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<Feedback>("/department/feedback", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDisposeFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, outcome }: { id: number; outcome: "resolved" | "archived" }) =>
      (await http.post<Feedback>(
        `/department/feedback/${id}/dispose`,
        { outcome })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReviewFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, category }: { id: number; category: string }) =>
      (await http.post<Feedback>(
        `/department/feedback/${id}/review`,
        { category })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Timetable ------------------------------------------------------------------
export function useTimetable() {
  return useQuery({
    queryKey: keys.timetable(),
    queryFn: async () =>
      (await http.get<Page<TimetableSlot>>("/department/timetable")).data,
    staleTime: 30_000,
  });
}
