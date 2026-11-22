/** Data access and query hooks for the Department module. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Announcement,
  DepartmentInfo,
  DepartmentRoleAssignment,
  Feedback,
  InventoryItem,
  LabResource,
  StockRequest,
  TimetableEntry,
  UserProfileExtension,
} from "./types";

const KEY = "dept";

export const keys = {
  announcements: (dept?: string) => [KEY, "announcements", dept] as const,
  inventory: (dept?: string) => [KEY, "inventory", dept] as const,
  stockRequests: (dept?: string, mine?: boolean) => [KEY, "stockRequests", dept, mine] as const,
  feedback: (dept?: string, mine?: boolean) => [KEY, "feedback", dept, mine] as const,
  timetables: (dept?: string, p?: string, y?: number, s?: number) => [KEY, "timetables", dept, p, y, s] as const,
  labs: (dept?: string) => [KEY, "labs", dept] as const,
  profiles: (dept?: string, t?: string) => [KEY, "profiles", dept, t] as const,
  details: (dept?: string) => [KEY, "details", dept] as const,
  pendingChanges: (dept?: string) => [KEY, "pendingChanges", dept] as const,
  roles: (dept?: string) => [KEY, "roles", dept] as const,
};

export function useDepartmentInfo(department?: string) {
  return useQuery({
    queryKey: keys.details(department),
    queryFn: async () => (await http.get<DepartmentInfo>("/dept/details/", { params: { department } })).data,
  });
}

export function useAnnouncements(params?: { department?: string; program?: string; year?: number }) {
  return useQuery({
    queryKey: keys.announcements(params?.department),
    queryFn: async () => (await http.get<Announcement[]>("/dept/announcements/", { params })).data,
  });
}

export function useCreateAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<Announcement>("/dept/announcements/", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, "announcements"] }),
  });
}

export function useInventoryItems(params?: { department?: string; category?: string }) {
  return useQuery({
    queryKey: keys.inventory(params?.department),
    queryFn: async () => (await http.get<InventoryItem[]>("/dept/inventory/", { params })).data,
  });
}

export function useCreateInventoryItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<InventoryItem>("/dept/inventory/", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, "inventory"] }),
  });
}

export function useAddStock(itemId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { quantity: number; notes?: string }) =>
      (await http.post<InventoryItem>(`/dept/inventory/${itemId}/add-stock/`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, "inventory"] }),
  });
}

export function useStockRequests(params?: { department?: string; mine?: boolean; status?: string }) {
  return useQuery({
    queryKey: keys.stockRequests(params?.department, params?.mine),
    queryFn: async () => (await http.get<StockRequest[]>("/dept/stock-requests/", { params })).data,
  });
}

export function useCreateStockRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<StockRequest>("/dept/stock-requests/", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, "stockRequests"] }),
  });
}

export function useDecideStockRequest(requestId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { decision: "APPROVE" | "REJECT"; remarks?: string }) =>
      (await http.post<StockRequest>(`/dept/stock-requests/${requestId}/decision/`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, "stockRequests"] }),
  });
}

export function useIssueStockRequest(requestId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { notes?: string }) =>
      (await http.post<StockRequest>(`/dept/stock-requests/${requestId}/issue/`, body)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "stockRequests"] });
      qc.invalidateQueries({ queryKey: [KEY, "inventory"] });
    },
  });
}

export function useFeedbackList(params?: { department?: string; mine?: boolean; status?: string }) {
  return useQuery({
    queryKey: keys.feedback(params?.department, params?.mine),
    queryFn: async () => (await http.get<Feedback[]>("/dept/feedback/", { params })).data,
  });
}

export function useSubmitFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<Feedback>("/dept/feedback/", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, "feedback"] }),
  });
}

export function useReviewFeedback(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { admin_remarks?: string }) =>
      (await http.post<Feedback>(`/dept/feedback/${id}/review/`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, "feedback"] }),
  });
}

export function useResolveFeedback(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { action: "RESOLVE" | "CLOSE"; remarks?: string }) =>
      (await http.post<Feedback>(`/dept/feedback/${id}/resolve/`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, "feedback"] }),
  });
}

export function useTimetables(params?: { department?: string; program?: string; year?: number; semester?: number }) {
  return useQuery({
    queryKey: keys.timetables(params?.department, params?.program, params?.year, params?.semester),
    queryFn: async () => (await http.get<TimetableEntry[]>("/dept/timetables/", { params })).data,
  });
}

export function useSaveTimetable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<TimetableEntry>("/dept/timetables/", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, "timetables"] }),
  });
}

export function useLabResources(params?: { department?: string }) {
  return useQuery({
    queryKey: keys.labs(params?.department),
    queryFn: async () => (await http.get<LabResource[]>("/dept/labs/", { params })).data,
  });
}

export function useProfiles(params?: { department?: string; type?: string }) {
  return useQuery({
    queryKey: keys.profiles(params?.department, params?.type),
    queryFn: async () => (await http.get<UserProfileExtension[]>("/dept/profiles/", { params })).data,
  });
}

export function useRoleAssignments(params?: { department?: string; active_only?: boolean }) {
  return useQuery({
    queryKey: keys.roles(params?.department),
    queryFn: async () => (await http.get<DepartmentRoleAssignment[]>("/dept/roles/", { params })).data,
  });
}

export function useAssignRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<DepartmentRoleAssignment>("/dept/roles/", body)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "roles"] });
      qc.invalidateQueries({ queryKey: [KEY, "details"] });
    },
  });
}
