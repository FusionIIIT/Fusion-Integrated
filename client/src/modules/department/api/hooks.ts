import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  Announcement,
  Department,
  DepartmentDetail,
  DepartmentDetailChange,
  DepartmentProfile,
  Feedback,
  InventoryItem,
  LabResource,
  Page,
  StockRequest,
  Timetable,
  TimetableSlot,
} from "./types";

const KEY = "department";

export const keys = {
  departments: () => [KEY, "departments"] as const,
  department: (id: number) => [KEY, "department", id] as const,
  announcements: (deptId?: number) => [KEY, "announcements", deptId] as const,
  inventory: (deptId?: number) => [KEY, "inventory", deptId] as const,
  stockRequests: (deptId?: number) => [KEY, "stock-requests", deptId] as const,
  feedback: (deptId?: number) => [KEY, "feedback", deptId] as const,
  profiles: (deptId?: number) => [KEY, "profiles", deptId] as const,
  timetables: (deptId?: number) => [KEY, "timetables", deptId] as const,
  slots: (timetableId?: number) => [KEY, "slots", timetableId] as const,
  resources: (deptId?: number) => [KEY, "resources", deptId] as const,
  details: (deptId?: number) => [KEY, "details", deptId] as const,
  changes: (deptId?: number) => [KEY, "changes", deptId] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Departments -----------------------------------------------------------------
export function useDepartments() {
  return useQuery({
    queryKey: keys.departments(),
    queryFn: async () => {
      const { data } = await http.get<Page<Department> | Department[]>("/department/departments/");
      return Array.isArray(data) ? data : data.results;
    },
  });
}

// -- Announcements ---------------------------------------------------------------
export function useAnnouncements(deptId?: number) {
  return useQuery({
    queryKey: keys.announcements(deptId),
    queryFn: async () => {
      const url = deptId
        ? `/department/announcements/?department=${deptId}`
        : "/department/announcements/";
      const { data } = await http.get<Page<Announcement> | Announcement[]>(url);
      return Array.isArray(data) ? data : data.results;
    },
  });
}

export function usePublishAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      department: number;
      title: string;
      body: string;
      academic_year?: string;
      programme?: string;
      role_target?: string;
    }) => {
      const { data } = await http.post<Announcement>("/department/announcements/", payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await http.delete(`/department/announcements/${id}/`);
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Inventory -------------------------------------------------------------------
export function useInventory(deptId?: number) {
  return useQuery({
    queryKey: keys.inventory(deptId),
    queryFn: async () => {
      const url = deptId
        ? `/department/inventory/?department=${deptId}`
        : "/department/inventory/";
      const { data } = await http.get<Page<InventoryItem> | InventoryItem[]>(url);
      return Array.isArray(data) ? data : data.results;
    },
  });
}

export function useCreateInventoryItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      department: number;
      name: string;
      quantity: number;
      unit?: string;
    }) => {
      const { data } = await http.post<InventoryItem>("/department/inventory/", payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useInsertStock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, quantity }: { id: number; quantity: number }) => {
      const { data } = await http.post<InventoryItem>(
        `/department/inventory/${id}/insert-stock/`,
        { quantity }
      );
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Stock Requests --------------------------------------------------------------
export function useStockRequests(deptId?: number) {
  return useQuery({
    queryKey: keys.stockRequests(deptId),
    queryFn: async () => {
      const url = deptId
        ? `/department/stock-requests/?department=${deptId}`
        : "/department/stock-requests/";
      const { data } = await http.get<Page<StockRequest> | StockRequest[]>(url);
      return Array.isArray(data) ? data : data.results;
    },
  });
}

export function useCreateStockRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      department: number;
      item: number;
      quantity: number;
    }) => {
      const { data } = await http.post<StockRequest>("/department/stock-requests/", payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDecideStockRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: number; status: "approved" | "rejected" }) => {
      const { data } = await http.post<StockRequest>(
        `/department/stock-requests/${id}/decide/`,
        { status }
      );
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useIssueStockRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await http.post<StockRequest>(
        `/department/stock-requests/${id}/issue/`,
        {}
      );
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Feedback --------------------------------------------------------------------
export function useFeedback(deptId?: number) {
  return useQuery({
    queryKey: keys.feedback(deptId),
    queryFn: async () => {
      const url = deptId
        ? `/department/feedback/?department=${deptId}`
        : "/department/feedback/";
      const { data } = await http.get<Page<Feedback> | Feedback[]>(url);
      return Array.isArray(data) ? data : data.results;
    },
  });
}

export function useSubmitFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      department: number;
      subject: string;
      body: string;
      category?: string;
    }) => {
      const { data } = await http.post<Feedback>("/department/feedback/", payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReviewFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, category }: { id: number; category: string }) => {
      const { data } = await http.post<Feedback>(`/department/feedback/${id}/review/`, {
        category,
      });
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useResolveFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: number; status: "resolved" | "closed" }) => {
      const { data } = await http.post<Feedback>(`/department/feedback/${id}/resolve/`, {
        status,
      });
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Profiles --------------------------------------------------------------------
export function useProfiles(deptId?: number) {
  return useQuery({
    queryKey: keys.profiles(deptId),
    queryFn: async () => {
      const url = deptId
        ? `/department/profiles/?department=${deptId}`
        : "/department/profiles/";
      const { data } = await http.get<Page<DepartmentProfile> | DepartmentProfile[]>(url);
      return Array.isArray(data) ? data : data.results;
    },
  });
}

// -- Timetables ------------------------------------------------------------------
export function useTimetables(deptId?: number) {
  return useQuery({
    queryKey: keys.timetables(deptId),
    queryFn: async () => {
      const url = deptId
        ? `/department/timetables/?department=${deptId}`
        : "/department/timetables/";
      const { data } = await http.get<Page<Timetable> | Timetable[]>(url);
      return Array.isArray(data) ? data : data.results;
    },
  });
}

export function useCreateTimetable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      department: number;
      title: string;
      academic_year?: string;
      programme?: string;
    }) => {
      const { data } = await http.post<Timetable>("/department/timetables/", payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useTimetableSlots(timetableId?: number) {
  return useQuery({
    queryKey: keys.slots(timetableId),
    queryFn: async () => {
      const url = timetableId
        ? `/department/timetable-slots/?timetable=${timetableId}`
        : "/department/timetable-slots/";
      const { data } = await http.get<Page<TimetableSlot> | TimetableSlot[]>(url);
      return Array.isArray(data) ? data : data.results;
    },
  });
}

export function useAddTimetableSlot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      timetable: number;
      day: string;
      start_time: string;
      end_time: string;
      subject: string;
      room?: string;
      faculty_user_id?: number | null;
    }) => {
      const { data } = await http.post<TimetableSlot>("/department/timetable-slots/", payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Lab Resources ---------------------------------------------------------------
export function useLabResources(deptId?: number) {
  return useQuery({
    queryKey: keys.resources(deptId),
    queryFn: async () => {
      const url = deptId
        ? `/department/resources/?department=${deptId}`
        : "/department/resources/";
      const { data } = await http.get<Page<LabResource> | LabResource[]>(url);
      return Array.isArray(data) ? data : data.results;
    },
  });
}

export function useUpsertResource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      department: number;
      name: string;
      description?: string;
      quantity?: number;
    }) => {
      const { data } = await http.post<LabResource>("/department/resources/", payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Details & Changes -----------------------------------------------------------
export function useDepartmentDetails(deptId?: number) {
  return useQuery({
    queryKey: keys.details(deptId),
    queryFn: async () => {
      const url = deptId
        ? `/department/details/?department=${deptId}`
        : "/department/details/";
      const { data } = await http.get<Page<DepartmentDetail> | DepartmentDetail[]>(url);
      return Array.isArray(data) ? data : data.results;
    },
  });
}

export function useDepartmentChanges(deptId?: number) {
  return useQuery({
    queryKey: keys.changes(deptId),
    queryFn: async () => {
      const url = deptId
        ? `/department/detail-changes/?department=${deptId}`
        : "/department/detail-changes/";
      const { data } = await http.get<Page<DepartmentDetailChange> | DepartmentDetailChange[]>(url);
      return Array.isArray(data) ? data : data.results;
    },
  });
}

export function useProposeDetailChange() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      department: number;
      field_name: string;
      proposed_value: string;
    }) => {
      const { data } = await http.post<DepartmentDetailChange>(
        "/department/detail-changes/",
        payload
      );
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDecideDetailChange() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: number; status: "approved" | "rejected" }) => {
      const { data } = await http.post<DepartmentDetailChange>(
        `/department/detail-changes/${id}/decide/`,
        { status }
      );
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}
