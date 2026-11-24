// One TanStack Query hook per endpoint; every mutation invalidates the whole module.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Announcement, AnnouncementInput, Department, Feedback, FeedbackNote, GeneralUpdate,
  InventoryItem, LabInput, LabResource, OfficialChange, Page, Profile, ProfileInput, RoleWarning,
  StockMovement, StockRequest, Tenure, TenureInput, TimetableSlot, TimetableSlotInput,
} from "./types";

const KEY = "department";
const BASE = "/department";

function useInvalidate() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

function useWrite<V, R>(fn: (vars: V) => Promise<R>) {
  const invalidate = useInvalidate();
  return useMutation({ mutationFn: fn, onSuccess: invalidate });
}

function useList<T>(path: string, params?: Record<string, string>) {
  return useQuery({
    queryKey: [KEY, path, params],
    queryFn: async () => (await http.get<Page<T>>(`${BASE}/${path}`, { params })).data,
  });
}

export function useDepartments() {
  return useQuery({
    queryKey: [KEY, "departments"],
    queryFn: async () => (await http.get<Department[]>(`${BASE}/departments`)).data,
  });
}

export function useDepartment(code: string | undefined) {
  return useQuery({
    queryKey: [KEY, "department", code],
    queryFn: async () => (await http.get<Department>(`${BASE}/departments/${code}`)).data,
    enabled: !!code,
  });
}

export const useUpdateDepartment = () =>
  useWrite(async ({ code, ...body }: GeneralUpdate & { code: string }) =>
    (await http.patch<Department>(`${BASE}/departments/${code}`, body)).data);

export function useOfficialChanges(enabled: boolean) {
  return useQuery({
    queryKey: [KEY, "official-changes"],
    queryFn: async () => (await http.get<Page<OfficialChange>>(`${BASE}/official-changes`)).data,
    enabled,
  });
}

export const useProposeChange = () =>
  useWrite(async (body: { field: OfficialChange["field"]; value: string }) =>
    (await http.post<OfficialChange>(`${BASE}/official-changes`, body)).data);

export const useDecideChange = () =>
  useWrite(async ({ id, ...body }: { id: number; approve: boolean; reason?: string }) =>
    (await http.post<OfficialChange>(`${BASE}/official-changes/${id}/decide`, body)).data);

export const useAnnouncements = () => useList<Announcement>("announcements");

export const usePublishAnnouncement = () =>
  useWrite(async (body: AnnouncementInput) =>
    (await http.post<Announcement>(`${BASE}/announcements`, body)).data);

export const useEditAnnouncement = () =>
  useWrite(async ({ id, ...body }: Partial<AnnouncementInput> & { id: number }) =>
    (await http.patch<Announcement>(`${BASE}/announcements/${id}`, body)).data);

export const useHideAnnouncement = () =>
  useWrite(async (id: number) =>
    (await http.post<Announcement>(`${BASE}/announcements/${id}/hide`)).data);

export const useDeleteAnnouncement = () =>
  useWrite(async (id: number) => {
    await http.delete(`${BASE}/announcements/${id}`);
  });

export const useInventoryItems = () => useList<InventoryItem>("inventory-items");

export const useAddItem = () =>
  useWrite(async (body: { name: string; unit: string; quantity: number }) =>
    (await http.post<InventoryItem>(`${BASE}/inventory-items`, body)).data);

export const useReceiveStock = () =>
  useWrite(async ({ id, quantity }: { id: number; quantity: number }) =>
    (await http.post<InventoryItem>(`${BASE}/inventory-items/${id}/receipts`, { quantity })).data);

export const useStockMovements = (enabled: boolean) =>
  useQuery({
    queryKey: [KEY, "stock-movements"],
    queryFn: async () => (await http.get<Page<StockMovement>>(`${BASE}/stock-movements`)).data,
    enabled,
  });

export const useStockRequests = (status?: string) =>
  useList<StockRequest>("stock-requests", status ? { status } : undefined);

export const useRequestStock = () =>
  useWrite(async (body: { item: number; quantity: number; purpose: string }) =>
    (await http.post<StockRequest>(`${BASE}/stock-requests`, body)).data);

export const useDecideStock = () =>
  useWrite(async ({ id, ...body }: { id: number; approve: boolean; reason?: string }) =>
    (await http.post<StockRequest>(`${BASE}/stock-requests/${id}/decide`, body)).data);

export const useIssueStock = () =>
  useWrite(async (id: number) =>
    (await http.post<StockRequest>(`${BASE}/stock-requests/${id}/issue`)).data);

export const useFeedback = () => useList<Feedback>("feedback");

export const useSubmitFeedback = () =>
  useWrite(async (body: { subject: string; body: string }) =>
    (await http.post<Feedback>(`${BASE}/feedback`, body)).data);

export const useReviewFeedback = () =>
  useWrite(async ({ id, ...body }: { id: number; category: string; disposition: string; note: string }) =>
    (await http.post<Feedback>(`${BASE}/feedback/${id}/review`, body)).data);

export const useDisposeFeedback = () =>
  useWrite(async ({ id, ...body }: { id: number; outcome: "resolved" | "closed"; note: string }) =>
    (await http.post<Feedback>(`${BASE}/feedback/${id}/dispose`, body)).data);

export const useAddFeedbackNote = () =>
  useWrite(async ({ id, body }: { id: number; body: string }) =>
    (await http.post<FeedbackNote>(`${BASE}/feedback/${id}/notes`, { body })).data);

export function useTimetable() {
  return useQuery({
    queryKey: [KEY, "timetable"],
    queryFn: async () => (await http.get<TimetableSlot[]>(`${BASE}/timetable-slots`)).data,
  });
}

export const useUploadSlots = () =>
  useWrite(async (slots: TimetableSlotInput[]) =>
    (await http.post<TimetableSlot[]>(`${BASE}/timetable-slots`, { slots })).data);

export const useEditSlot = () =>
  useWrite(async ({ id, ...body }: Partial<TimetableSlotInput> & { id: number }) =>
    (await http.patch<TimetableSlot>(`${BASE}/timetable-slots/${id}`, body)).data);

export const useDeleteSlot = () =>
  useWrite(async (id: number) => {
    await http.delete(`${BASE}/timetable-slots/${id}`);
  });

export const useLabs = () => useList<LabResource>("lab-resources");

export const useSaveLab = () =>
  useWrite(async ({ id, ...body }: LabInput & { id?: number }) =>
    id == null
      ? (await http.post<LabResource>(`${BASE}/lab-resources`, body)).data
      : (await http.patch<LabResource>(`${BASE}/lab-resources/${id}`, body)).data);

export const useProfiles = () => useList<Profile>("profiles");

export const useCreateProfile = () =>
  useWrite(async (body: ProfileInput) =>
    (await http.post<Profile>(`${BASE}/profiles`, body)).data);

export const useUpdateProfile = () =>
  useWrite(async ({ id, ...body }: Partial<ProfileInput> & { id: number; is_active?: boolean }) =>
    (await http.patch<Profile>(`${BASE}/profiles/${id}`, body)).data);

export const useTenures = () => useList<Tenure>("role-assignments");

export const useAssignTenure = () =>
  useWrite(async (body: TenureInput) =>
    (await http.post<Tenure>(`${BASE}/role-assignments`, body)).data);

export const useChangeTenure = () =>
  useWrite(async ({ id, valid_to }: { id: number; valid_to: string }) =>
    (await http.patch<Tenure>(`${BASE}/role-assignments/${id}`, { valid_to })).data);

export function useRoleWarnings() {
  return useQuery({
    queryKey: [KEY, "role-vacancies"],
    queryFn: async () => (await http.get<RoleWarning[]>(`${BASE}/role-assignments/vacancies`)).data,
  });
}
