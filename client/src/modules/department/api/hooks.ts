import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Announcement, DepartmentDetails, Feedback, InventoryItem, Page,
  ResourceProfile, StockMovement, StockRequest, TimetableEntry,
} from "./types";

const BASE = "/department";
const KEY = ["department"] as const;

function useDepartmentMutation<T>(send: (data: T) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: send,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useAnnouncements() {
  return useQuery({
    queryKey: [...KEY, "announcements"],
    queryFn: async () => (await http.get<Page<Announcement>>(
      `${BASE}/announcements`)).data.results,
  });
}

export function useCreateAnnouncement() {
  return useDepartmentMutation((data: Record<string, unknown>) =>
    http.post(`${BASE}/announcements`, data));
}

export function useAnnouncementAction() {
  return useDepartmentMutation((data: {
    id: number; action: "edit" | "hide" | "delete"; payload?: Record<string, unknown>;
  }) => http.post(`${BASE}/announcements/${data.id}/${data.action}`, data.payload ?? {}));
}

export function useInventory() {
  return useQuery({
    queryKey: [...KEY, "inventory"],
    queryFn: async () => (await http.get<{
      items: InventoryItem[]; movements: StockMovement[];
    }>(`${BASE}/inventory`)).data,
  });
}

export function useStockRequests() {
  return useQuery({
    queryKey: [...KEY, "stock-requests"],
    queryFn: async () => (await http.get<Page<StockRequest>>(
      `${BASE}/stock-requests`)).data.results,
  });
}

export function useAddStock() {
  return useDepartmentMutation((data: Record<string, unknown>) =>
    http.post(`${BASE}/inventory`, data));
}

export function useRequestStock() {
  return useDepartmentMutation((data: { item_id: number; quantity: number }) =>
    http.post(`${BASE}/stock-requests`, data));
}

export function useStockAction() {
  return useDepartmentMutation((data: { id: number; action: string; note?: string }) =>
    http.post(`${BASE}/stock-requests/${data.id}/${data.action}`, { note: data.note ?? "" }));
}

export function useFeedback() {
  return useQuery({
    queryKey: [...KEY, "feedback"],
    queryFn: async () => (await http.get<Page<Feedback>>(
      `${BASE}/feedback`)).data.results,
  });
}

export function useCreateFeedback() {
  return useDepartmentMutation((data: { body: string }) =>
    http.post(`${BASE}/feedback`, data));
}

export function useFeedbackAction() {
  return useDepartmentMutation((data: {
    id: number; payload: Record<string, string>;
  }) => http.post(`${BASE}/feedback/${data.id}/review`, data.payload));
}

export function useResources() {
  return useQuery({
    queryKey: [...KEY, "resources"],
    queryFn: async () => (await http.get<Page<ResourceProfile>>(
      `${BASE}/resources`)).data.results,
  });
}

export function useCreateResource() {
  return useDepartmentMutation((data: Record<string, unknown>) =>
    http.post(`${BASE}/resources`, data));
}

export function useUpdateResource() {
  return useDepartmentMutation((data: { id: number; payload: Record<string, unknown> }) =>
    http.patch(`${BASE}/resources/${data.id}`, data.payload));
}

export function useTimetable(enabled = true) {
  return useQuery({
    queryKey: [...KEY, "timetable"],
    queryFn: async () => (await http.get<Page<TimetableEntry>>(
      `${BASE}/timetables`)).data.results,
    enabled,
  });
}

export function useCreateTimetableEntry() {
  return useDepartmentMutation((data: Record<string, unknown>) =>
    http.post(`${BASE}/timetables`, data));
}

export function useUpdateTimetableEntry() {
  return useDepartmentMutation((data: { id: number; payload: Record<string, unknown> }) =>
    http.put(`${BASE}/timetables/${data.id}`, data.payload));
}

export function useDepartmentDetails(enabled = true) {
  return useQuery({
    queryKey: [...KEY, "details"],
    queryFn: async () => (await http.get<DepartmentDetails>(
      `${BASE}/details`)).data,
    enabled,
  });
}

export function useUpdateGeneralDetails() {
  return useDepartmentMutation((data: { general: Record<string, unknown> }) =>
    http.patch(`${BASE}/details`, data));
}

export function useProposeOfficialChange() {
  return useDepartmentMutation((data: { field_name: string; proposed_value: unknown }) =>
    http.post(`${BASE}/details`, data));
}

export function useDepartmentChangeAction() {
  return useDepartmentMutation((data: { id: number; action: "approve" | "reject" }) =>
    http.post(`${BASE}/details/changes/${data.id}/${data.action}`, {}));
}
