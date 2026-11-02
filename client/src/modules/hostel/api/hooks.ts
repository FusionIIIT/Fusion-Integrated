/** Data access hooks for Hostel Management (HM) module. */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  AccommodationRequest,
  AttendanceRecord,
  DashboardStats,
  ExtendedStayRequest,
  GuestRoomBooking,
  Hostel,
  HostelComplaint,
  HostelFine,
  HostelInventory,
  HostelLeave,
  HostelNotice,
  HostelNotification,
  HostelRoleBinding,
  HostelStaff,
  Page,
  Room,
  RoomAllotment,
  SecurityShift,
} from "./types";

const KEY = "hostel";

export const keys = {
  all: [KEY] as const,
  hostels: (filters?: unknown) => [KEY, "hostels", filters] as const,
  hostel: (id: number) => [KEY, "hostel", id] as const,
  roleBindings: (filters?: unknown) => [KEY, "role-bindings", filters] as const,
  rooms: (filters?: unknown) => [KEY, "rooms", filters] as const,
  accommodationRequests: (filters?: unknown) => [KEY, "accommodation-requests", filters] as const,
  allotments: (filters?: unknown) => [KEY, "allotments", filters] as const,
  attendance: (filters?: unknown) => [KEY, "attendance", filters] as const,
  leaves: (filters?: unknown) => [KEY, "leaves", filters] as const,
  complaints: (filters?: unknown) => [KEY, "complaints", filters] as const,
  guestRooms: (filters?: unknown) => [KEY, "guest-rooms", filters] as const,
  extendedStays: (filters?: unknown) => [KEY, "extended-stays", filters] as const,
  fines: (filters?: unknown) => [KEY, "fines", filters] as const,
  inventory: (filters?: unknown) => [KEY, "inventory", filters] as const,
  staff: (filters?: unknown) => [KEY, "staff", filters] as const,
  securityShifts: (filters?: unknown) => [KEY, "security-shifts", filters] as const,
  notices: (filters?: unknown) => [KEY, "notices", filters] as const,
  notifications: () => [KEY, "notifications"] as const,
  dashboardStats: () => [KEY, "dashboard-stats"] as const,
  reports: (params?: unknown) => [KEY, "reports", params] as const,
  summary: () => [KEY, "summary"] as const,
};

function invalidate(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// --- Hostels & Role Bindings ---

export function useHostels(filters?: { is_active?: boolean; gender?: string }) {
  return useQuery({
    queryKey: keys.hostels(filters),
    queryFn: async () => (await http.get<Page<Hostel>>("/hostel/hostels/", { params: filters })).data,
  });
}

export function useCreateHostel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Hostel>) => (await http.post<Hostel>("/hostel/hostels/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useToggleHostelActive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, is_active }: { id: number; is_active: boolean }) =>
      (await http.post<Hostel>(`/hostel/hostels/${id}/toggle-active/`, { is_active })).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useRoleBindings(filters?: { hostel_id?: number; role?: string }) {
  return useQuery({
    queryKey: keys.roleBindings(filters),
    queryFn: async () =>
      (await http.get<Page<HostelRoleBinding>>("/hostel/role-bindings/", { params: filters })).data,
  });
}

export function useCreateRoleBinding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<HostelRoleBinding>) =>
      (await http.post<HostelRoleBinding>("/hostel/role-bindings/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useDeactivateRoleBinding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<HostelRoleBinding>(`/hostel/role-bindings/${id}/deactivate/`)).data,
    onSuccess: () => invalidate(qc),
  });
}

// --- Rooms ---

export function useRooms(filters?: { hostel_id?: number; floor?: number; status?: string }) {
  return useQuery({
    queryKey: keys.rooms(filters),
    queryFn: async () => (await http.get<Page<Room>>("/hostel/rooms/", { params: filters })).data,
  });
}

export function useCreateRoom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Room>) => (await http.post<Room>("/hostel/rooms/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useUpdateRoomStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status, remarks }: { id: number; status: string; remarks?: string }) =>
      (await http.patch<Room>(`/hostel/rooms/${id}/status/`, { status, remarks })).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useRoomExchange() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { allotment_a_id: number; allotment_b_id: number; reason?: string }) =>
      (await http.post("/hostel/rooms/exchange/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

// --- Accommodation & Allotments ---

export function useAccommodationRequests(filters?: { hostel_id?: number; status?: string }) {
  return useQuery({
    queryKey: keys.accommodationRequests(filters),
    queryFn: async () =>
      (await http.get<Page<AccommodationRequest>>("/hostel/accommodation-requests/", { params: filters })).data,
  });
}

export function useCreateAccommodationRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<AccommodationRequest>) =>
      (await http.post<AccommodationRequest>("/hostel/accommodation-requests/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useAllotments(filters?: { hostel_id?: number; status?: string; student_user_id?: number }) {
  return useQuery({
    queryKey: keys.allotments(filters),
    queryFn: async () =>
      (await http.get<Page<RoomAllotment>>("/hostel/allotments/", { params: filters })).data,
  });
}

export function useCreateAllotment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      student_user_id: number;
      hostel: number;
      room: number;
      bed_number: string;
      linked_request_id?: number;
    }) => (await http.post<RoomAllotment>("/hostel/allotments/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useVacateAllotment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remarks, clearance }: { id: number; remarks?: string; clearance?: boolean }) =>
      (
        await http.post<RoomAllotment>(`/hostel/allotments/${id}/vacate/`, {
          vacation_remarks: remarks,
          vacation_clearance_status: clearance ?? true,
        })
      ).data,
    onSuccess: () => invalidate(qc),
  });
}

// --- Attendance ---

export function useAttendance(filters?: { hostel_id?: number; date?: string; student_user_id?: number }) {
  return useQuery({
    queryKey: keys.attendance(filters),
    queryFn: async () =>
      (await http.get<Page<AttendanceRecord>>("/hostel/attendance/", { params: filters })).data,
  });
}

export function useRecordAttendance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      hostel_id: number;
      attendance_date: string;
      records: Array<{ student_user_id: number; status: string; remarks?: string }>;
    }) => (await http.post("/hostel/attendance/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

// --- Leaves ---

export function useLeaves(filters?: { hostel_id?: number; status?: string }) {
  return useQuery({
    queryKey: keys.leaves(filters),
    queryFn: async () => (await http.get<Page<HostelLeave>>("/hostel/leaves/", { params: filters })).data,
  });
}

export function useCreateLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<HostelLeave>) =>
      (await http.post<HostelLeave>("/hostel/leaves/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useDecideLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, decision, remarks }: { id: number; decision: string; remarks?: string }) =>
      (await http.post<HostelLeave>(`/hostel/leaves/${id}/decide/`, { decision, remarks })).data,
    onSuccess: () => invalidate(qc),
  });
}

// --- Complaints ---

export function useComplaints(filters?: { hostel_id?: number; status?: string; category?: string }) {
  return useQuery({
    queryKey: keys.complaints(filters),
    queryFn: async () =>
      (await http.get<Page<HostelComplaint>>("/hostel/complaints/", { params: filters })).data,
  });
}

export function useCreateComplaint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<HostelComplaint>) =>
      (await http.post<HostelComplaint>("/hostel/complaints/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useUpdateComplaintStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      status,
      assigned_worker,
      resolution_notes,
    }: {
      id: number;
      status: string;
      assigned_worker?: string;
      resolution_notes?: string;
    }) =>
      (
        await http.patch<HostelComplaint>(`/hostel/complaints/${id}/update-status/`, {
          status,
          assigned_worker,
          resolution_notes,
        })
      ).data,
    onSuccess: () => invalidate(qc),
  });
}

// --- Guest Rooms ---

export function useGuestRooms(filters?: { hostel_id?: number; status?: string }) {
  return useQuery({
    queryKey: keys.guestRooms(filters),
    queryFn: async () =>
      (await http.get<Page<GuestRoomBooking>>("/hostel/guest-rooms/", { params: filters })).data,
  });
}

export function useCreateGuestRoomBooking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<GuestRoomBooking>) =>
      (await http.post<GuestRoomBooking>("/hostel/guest-rooms/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useDecideGuestRoomBooking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      decision,
      allocated_room_number,
      charges,
      remarks,
    }: {
      id: number;
      decision: string;
      allocated_room_number?: string;
      charges?: number | string;
      remarks?: string;
    }) =>
      (
        await http.post<GuestRoomBooking>(`/hostel/guest-rooms/${id}/decide/`, {
          decision,
          allocated_room_number,
          charges,
          remarks,
        })
      ).data,
    onSuccess: () => invalidate(qc),
  });
}

// --- Extended Stays ---

export function useExtendedStays(filters?: { hostel_id?: number; status?: string }) {
  return useQuery({
    queryKey: keys.extendedStays(filters),
    queryFn: async () =>
      (await http.get<Page<ExtendedStayRequest>>("/hostel/extended-stays/", { params: filters })).data,
  });
}

export function useCreateExtendedStay() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<ExtendedStayRequest>) =>
      (await http.post<ExtendedStayRequest>("/hostel/extended-stays/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useDecideExtendedStay() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      decision,
      charge_amount,
      payment_deadline,
      remarks,
    }: {
      id: number;
      decision: string;
      charge_amount?: number | string;
      payment_deadline?: string;
      remarks?: string;
    }) =>
      (
        await http.post<ExtendedStayRequest>(`/hostel/extended-stays/${id}/decide/`, {
          decision,
          charge_amount,
          payment_deadline,
          remarks,
        })
      ).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useUpdateExtendedStayCompliance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, compliance_status, remarks }: { id: number; compliance_status: string; remarks?: string }) =>
      (
        await http.patch<ExtendedStayRequest>(`/hostel/extended-stays/${id}/compliance/`, {
          compliance_status,
          remarks,
        })
      ).data,
    onSuccess: () => invalidate(qc),
  });
}

// --- Fines ---

export function useFines(filters?: { hostel_id?: number; status?: string; student_user_id?: number }) {
  return useQuery({
    queryKey: keys.fines(filters),
    queryFn: async () => (await http.get<Page<HostelFine>>("/hostel/fines/", { params: filters })).data,
  });
}

export function useCreateFine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<HostelFine>) =>
      (await http.post<HostelFine>("/hostel/fines/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useUpdateFineStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      status,
      receipt_reference,
      remarks,
    }: {
      id: number;
      status: string;
      receipt_reference?: string;
      remarks?: string;
    }) =>
      (
        await http.patch<HostelFine>(`/hostel/fines/${id}/update-status/`, {
          status,
          receipt_reference,
          remarks,
        })
      ).data,
    onSuccess: () => invalidate(qc),
  });
}

// --- Inventory & Staff ---

export function useInventory(filters?: { hostel_id?: number; category?: string }) {
  return useQuery({
    queryKey: keys.inventory(filters),
    queryFn: async () =>
      (await http.get<Page<HostelInventory>>("/hostel/inventory/", { params: filters })).data,
  });
}

export function useCreateInventory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<HostelInventory>) =>
      (await http.post<HostelInventory>("/hostel/inventory/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useStaff(filters?: { hostel_id?: number; role?: string; is_active?: boolean }) {
  return useQuery({
    queryKey: keys.staff(filters),
    queryFn: async () => (await http.get<Page<HostelStaff>>("/hostel/staff/", { params: filters })).data,
  });
}

export function useCreateStaff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<HostelStaff>) =>
      (await http.post<HostelStaff>("/hostel/staff/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

// --- Security Shifts ---

export function useSecurityShifts(filters?: { hostel_id?: number; shift_date?: string }) {
  return useQuery({
    queryKey: keys.securityShifts(filters),
    queryFn: async () =>
      (await http.get<Page<SecurityShift>>("/hostel/security-shifts/", { params: filters })).data,
  });
}

export function useCreateSecurityShift() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<SecurityShift>) =>
      (await http.post<SecurityShift>("/hostel/security-shifts/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

// --- Notices ---

export function useNotices(filters?: { hostel_id?: number; is_active?: boolean }) {
  return useQuery({
    queryKey: keys.notices(filters),
    queryFn: async () =>
      (await http.get<Page<HostelNotice>>("/hostel/notices/", { params: filters })).data,
  });
}

export function useCreateNotice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<HostelNotice>) =>
      (await http.post<HostelNotice>("/hostel/notices/", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

// --- Notifications ---

export function useNotifications() {
  return useQuery({
    queryKey: keys.notifications(),
    queryFn: async () =>
      (await http.get<Page<HostelNotification>>("/hostel/notifications/")).data,
  });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post(`/hostel/notifications/${id}/read/`)).data,
    onSuccess: () => invalidate(qc),
  });
}

// --- Dashboards & Reports ---

export function useDashboardStats() {
  return useQuery({
    queryKey: keys.dashboardStats(),
    queryFn: async () => (await http.get<DashboardStats>("/hostel/dashboard/stats/")).data,
  });
}

export function useHostelReports(params?: { type?: string; hostel_id?: number }) {
  return useQuery({
    queryKey: keys.reports(params),
    queryFn: async () => (await http.get<any>("/hostel/reports/", { params })).data,
  });
}

export function useExecutiveSummary() {
  return useQuery({
    queryKey: keys.summary(),
    queryFn: async () => (await http.get<any>("/hostel/reports/summary/")).data,
  });
}
