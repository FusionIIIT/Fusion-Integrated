/** Data access for the department module. Mutations invalidate the whole
 *  module key: these pages are small and correctness beats shaving a refetch. */
import {
  useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Announcement, Feedback, InventoryItem, StockMovement, StockRequest,
} from "./types";

const KEY = "dept";

function useInvalidate() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

// -- announcements ---------------------------------------------------------------
export function useAnnouncements() {
  return useQuery({
    queryKey: [KEY, "announcements"],
    queryFn: async () =>
      (await http.get<Announcement[]>("/dept/announcements")).data,
  });
}

export function usePublishAnnouncement() {
  const done = useInvalidate();
  return useMutation({
    mutationFn: async (body: {
      title: string; body: string; target_roles: string[];
      target_programmes: string[]; target_years: number[];
    }) => (await http.post<Announcement>("/dept/announcements", body)).data,
    onSuccess: done,
  });
}

export function useSetAnnouncementStatus() {
  const done = useInvalidate();
  return useMutation({
    mutationFn: async ({ id, status }: { id: number; status: string }) =>
      (await http.post<Announcement>(
        `/dept/announcements/${id}/status`, { status })).data,
    onSuccess: done,
  });
}

// -- inventory & stock -----------------------------------------------------------
export function useInventory() {
  return useQuery({
    queryKey: [KEY, "inventory"],
    queryFn: async () => (await http.get<InventoryItem[]>("/dept/inventory")).data,
  });
}

export function useAddInventory() {
  const done = useInvalidate();
  return useMutation({
    mutationFn: async (body: {
      name: string; quantity: number; category?: string; unit?: string;
    }) => (await http.post<InventoryItem>("/dept/inventory", body)).data,
    onSuccess: done,
  });
}

export function useStockRequests() {
  return useQuery({
    queryKey: [KEY, "stock-requests"],
    queryFn: async () =>
      (await http.get<StockRequest[]>("/dept/stock-requests")).data,
  });
}

export function useRequestStock() {
  const done = useInvalidate();
  return useMutation({
    mutationFn: async (body: { item: number; quantity: number; purpose: string }) =>
      (await http.post<StockRequest>("/dept/stock-requests", body)).data,
    onSuccess: done,
  });
}

export function useDecideStock() {
  const done = useInvalidate();
  return useMutation({
    mutationFn: async ({ id, approve, note }:
      { id: number; approve: boolean; note: string }) =>
      (await http.post<StockRequest>(
        `/dept/stock-requests/${id}/decision`, { approve, note })).data,
    onSuccess: done,
  });
}

export function useIssueStock() {
  const done = useInvalidate();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<StockRequest>(`/dept/stock-requests/${id}/issue`)).data,
    onSuccess: done,
  });
}

export function useStockLog(enabled: boolean) {
  return useQuery({
    queryKey: [KEY, "stock-log"],
    enabled,
    queryFn: async () => (await http.get<StockMovement[]>("/dept/stock-log")).data,
  });
}

// -- feedback --------------------------------------------------------------------
export function useFeedback() {
  return useQuery({
    queryKey: [KEY, "feedback"],
    queryFn: async () => (await http.get<Feedback[]>("/dept/feedback")).data,
  });
}

export function useSubmitFeedback() {
  const done = useInvalidate();
  return useMutation({
    mutationFn: async (body: { subject: string; body: string }) =>
      (await http.post<Feedback>("/dept/feedback", body)).data,
    onSuccess: done,
  });
}

export function useMoveFeedback() {
  const done = useInvalidate();
  return useMutation({
    mutationFn: async ({ id, ...body }: {
      id: number; to_status: string; category?: string; note?: string;
    }) => (await http.post<Feedback>(`/dept/feedback/${id}/transition`, body)).data,
    onSuccess: done,
  });
}
