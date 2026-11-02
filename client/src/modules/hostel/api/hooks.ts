/** React Query data hooks for Hostel Management. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { http, errorMessage } from "../../../lib/http";
import type {
  AccommodationRequest,
  AttendanceRecord,
  ExtendedStayRequest,
  GuestRoomBooking,
  Hostel,
  HostelComplaint,
  HostelFine,
  HostelInventoryItem,
  HostelNotice,
  HostelRoleBinding,
  InventoryAuditLog,
  LeaveRequest,
  NotificationRecord,
  OperationalReport,
  Room,
  RoomAllotment,
  RoomAssignmentHistory,
  SecurityGuardShift,
  StaffAssignment,
} from "./types";

const KEY = "hostel";

export const keys = {
  hostels: (f?: unknown) => [KEY, "hostels", f] as const,
  hostel: (id: number) => [KEY, "hostel", id] as const,
  bindings: (f?: unknown) => [KEY, "bindings", f] as const,
  rooms: (f?: unknown) => [KEY, "rooms", f] as const,
  requests: (f?: unknown) => [KEY, "requests", f] as const,
  allotments: (f?: unknown) => [KEY, "allotments", f] as const,
  history: (f?: unknown) => [KEY, "history", f] as const,
  attendance: (f?: unknown) => [KEY, "attendance", f] as const,
  leaves: (f?: unknown) => [KEY, "leaves", f] as const,
  complaints: (f?: unknown) => [KEY, "complaints", f] as const,
  guestRooms: (f?: unknown) => [KEY, "guestRooms", f] as const,
  extendedStays: (f?: unknown) => [KEY, "extendedStays", f] as const,
  fines: (f?: unknown) => [KEY, "fines", f] as const,
  inventory: (f?: unknown) => [KEY, "inventory", f] as const,
  inventoryAudits: (f?: unknown) => [KEY, "inventoryAudits", f] as const,
  staff: (f?: unknown) => [KEY, "staff", f] as const,
  security: (f?: unknown) => [KEY, "security", f] as const,
  notices: (f?: unknown) => [KEY, "notices", f] as const,
  notifications: () => [KEY, "notifications"] as const,
  reports: (f?: unknown) => [KEY, "reports", f] as const,
};

function notifySuccess(message: string) {
  notifications.show({ color: "teal", message });
}

function notifyError(e: unknown, title = "Operation Failed") {
  notifications.show({ color: "red", title, message: errorMessage(e) });
}

// -- Hostels --
export function useHostels(filters?: { is_active?: boolean }) {
  return useQuery({
    queryKey: keys.hostels(filters),
    queryFn: async () => {
      const res = await http.get<Hostel[]>("/hostel/hostels/", { params: filters });
      return res.data;
    },
  });
}

export function useCreateHostel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Hostel>) => {
      const res = await http.post<Hostel>("/hostel/hostels/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "hostels"] });
      notifySuccess("Hostel created successfully.");
    },
    onError: (e) => notifyError(e),
  });
}

export function useToggleHostelActive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, is_active }: { id: number; is_active: boolean }) => {
      const res = await http.post<Hostel>(`/hostel/hostels/${id}/toggle-active/`, { is_active });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "hostels"] });
      notifySuccess("Hostel status updated.");
    },
    onError: (e) => notifyError(e),
  });
}

// -- Role Bindings --
export function useRoleBindings(hostel_id?: number) {
  return useQuery({
    queryKey: keys.bindings({ hostel_id }),
    queryFn: async () => {
      const res = await http.get<HostelRoleBinding[]>("/hostel/role-bindings/", { params: { hostel_id } });
      return res.data;
    },
  });
}

export function useCreateRoleBinding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: any) => {
      const res = await http.post<HostelRoleBinding>("/hostel/role-bindings/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "bindings"] });
      notifySuccess("Hostel role binding updated.");
    },
    onError: (e) => notifyError(e),
  });
}

// -- Rooms --
export function useRooms(filters?: { hostel_id?: number; floor?: number }) {
  return useQuery({
    queryKey: keys.rooms(filters),
    queryFn: async () => {
      const res = await http.get<Room[]>("/hostel/rooms/", { params: filters });
      return res.data;
    },
  });
}

export function useCreateRoom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: any) => {
      const res = await http.post<Room>("/hostel/rooms/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "rooms"] });
      notifySuccess("Room created successfully.");
    },
    onError: (e) => notifyError(e),
  });
}

export function useRoomExchange() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: any) => {
      const res = await http.post("/hostel/rooms/exchange/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
      notifySuccess("Room exchange executed successfully.");
    },
    onError: (e) => notifyError(e),
  });
}

// -- Accommodation & Allotments --
export function useAccommodationRequests(filters?: { hostel_id?: number; status?: string }) {
  return useQuery({
    queryKey: keys.requests(filters),
    queryFn: async () => {
      const res = await http.get<AccommodationRequest[]>("/hostel/accommodation-requests/", { params: filters });
      return res.data;
    },
  });
}

export function useSubmitAccommodationRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: any) => {
      const res = await http.post<AccommodationRequest>("/hostel/accommodation-requests/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "requests"] });
      notifySuccess("Accommodation request submitted successfully.");
    },
    onError: (e) => notifyError(e),
  });
}

export function useAllotRoom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ requestId, roomId, reason }: { requestId: number; roomId: number; reason?: string }) => {
      const res = await http.post(`/hostel/accommodation-requests/${requestId}/allot/`, { room_id: roomId, reason });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
      notifySuccess("Room allotted successfully.");
    },
    onError: (e) => notifyError(e),
  });
}

export function useAllotments(filters?: { hostel_id?: number; is_active?: boolean }) {
  return useQuery({
    queryKey: keys.allotments(filters),
    queryFn: async () => {
      const res = await http.get<RoomAllotment[]>("/hostel/allotments/", { params: filters });
      return res.data;
    },
  });
}

export function useReallotRoom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ allotmentId, newRoomId, reason }: { allotmentId: number; newRoomId: number; reason?: string }) => {
      const res = await http.post(`/hostel/allotments/${allotmentId}/reallot/`, { new_room_id: newRoomId, reason });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
      notifySuccess("Room re-allotment recorded.");
    },
    onError: (e) => notifyError(e),
  });
}

export function useVacateRoom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ allotmentId, reason }: { allotmentId: number; reason?: string }) => {
      const res = await http.post(`/hostel/allotments/${allotmentId}/vacate/`, { reason });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
      notifySuccess("Room vacation recorded.");
    },
    onError: (e) => notifyError(e),
  });
}

export function useRoomHistory(filters?: { student_user_id?: number; room_id?: number }) {
  return useQuery({
    queryKey: keys.history(filters),
    queryFn: async () => {
      const res = await http.get<RoomAssignmentHistory[]>("/hostel/allotments/history/", { params: filters });
      return res.data;
    },
  });
}

// -- Attendance --
export function useAttendance(filters?: { hostel_id?: number; date?: string; from_date?: string; to_date?: string }) {
  return useQuery({
    queryKey: keys.attendance(filters),
    queryFn: async () => {
      const res = await http.get<AttendanceRecord[]>("/hostel/attendance/", { params: filters });
      return res.data;
    },
  });
}

export function useRecordAttendance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: any) => {
      const res = await http.post("/hostel/attendance/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "attendance"] });
      notifySuccess("Attendance saved successfully.");
    },
    onError: (e) => notifyError(e),
  });
}

// -- Leaves --
export function useLeaves(filters?: { hostel_id?: number; status?: string }) {
  return useQuery({
    queryKey: keys.leaves(filters),
    queryFn: async () => {
      const res = await http.get<LeaveRequest[]>("/hostel/leaves/", { params: filters });
      return res.data;
    },
  });
}

export function useSubmitLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: any) => {
      const res = await http.post<LeaveRequest>("/hostel/leaves/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "leaves"] });
      notifySuccess("Leave request submitted.");
    },
    onError: (e) => notifyError(e),
  });
}

export function useLeaveDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, decision, remarks }: { id: number; decision: string; remarks?: string }) => {
      const res = await http.post(`/hostel/leaves/${id}/decision/`, { decision, remarks });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY] });
      notifySuccess("Leave decision saved.");
    },
    onError: (e) => notifyError(e),
  });
}

// -- Complaints --
export function useComplaints(filters?: { hostel_id?: number; status?: string; escalated_only?: boolean }) {
  return useQuery({
    queryKey: keys.complaints(filters),
    queryFn: async () => {
      const res = await http.get<HostelComplaint[]>("/hostel/complaints/", { params: filters });
      return res.data;
    },
  });
}

export function useSubmitComplaint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: any) => {
      const res = await http.post<HostelComplaint>("/hostel/complaints/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "complaints"] });
      notifySuccess("Complaint lodged successfully.");
    },
    onError: (e) => notifyError(e),
  });
}

export function useUpdateComplaintStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: any }) => {
      const res = await http.post(`/hostel/complaints/${id}/status/`, data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "complaints"] });
      notifySuccess("Complaint updated.");
    },
    onError: (e) => notifyError(e),
  });
}

// -- Guest Rooms --
export function useGuestBookings(filters?: { hostel_id?: number; status?: string }) {
  return useQuery({
    queryKey: keys.guestRooms(filters),
    queryFn: async () => {
      const res = await http.get<GuestRoomBooking[]>("/hostel/guest-rooms/", { params: filters });
      return res.data;
    },
  });
}

export function useSubmitGuestBooking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: any) => {
      const res = await http.post<GuestRoomBooking>("/hostel/guest-rooms/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "guestRooms"] });
      notifySuccess("Guest room booking requested.");
    },
    onError: (e) => notifyError(e),
  });
}

export function useGuestBookingDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, decision, assigned_room_id, remarks }: any) => {
      const res = await http.post(`/hostel/guest-rooms/${id}/decision/`, {
        decision,
        assigned_room_id,
        remarks,
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "guestRooms"] });
      notifySuccess("Guest room decision recorded.");
    },
    onError: (e) => notifyError(e),
  });
}

// -- Extended Stay --
export function useExtendedStays(filters?: { hostel_id?: number; status?: string }) {
  return useQuery({
    queryKey: keys.extendedStays(filters),
    queryFn: async () => {
      const res = await http.get<ExtendedStayRequest[]>("/hostel/extended-stay/", { params: filters });
      return res.data;
    },
  });
}

export function useSubmitExtendedStay() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: any) => {
      const res = await http.post<ExtendedStayRequest>("/hostel/extended-stay/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "extendedStays"] });
      notifySuccess("Extended stay request submitted.");
    },
    onError: (e) => notifyError(e),
  });
}

export function useExtendedStayDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, decision, remarks }: any) => {
      const res = await http.post(`/hostel/extended-stay/${id}/decision/`, { decision, remarks });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "extendedStays"] });
      notifySuccess("Extended stay decision recorded.");
    },
    onError: (e) => notifyError(e),
  });
}

export function useExtendedStayCompliance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: any) => {
      const res = await http.post(`/hostel/extended-stay/${id}/compliance/`, data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "extendedStays"] });
      notifySuccess("Fee and compliance updated.");
    },
    onError: (e) => notifyError(e),
  });
}

// -- Fines --
export function useFines(filters?: { hostel_id?: number }) {
  return useQuery({
    queryKey: keys.fines(filters),
    queryFn: async () => {
      const res = await http.get<HostelFine[]>("/hostel/fines/", { params: filters });
      return res.data;
    },
  });
}

export function useRecordFine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: any) => {
      const res = await http.post<HostelFine>("/hostel/fines/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "fines"] });
      notifySuccess("Fine imposed and recorded.");
    },
    onError: (e) => notifyError(e),
  });
}

// -- Inventory & Staff --
export function useInventory(filters?: { hostel_id?: number; category?: string }) {
  return useQuery({
    queryKey: keys.inventory(filters),
    queryFn: async () => {
      const res = await http.get<HostelInventoryItem[]>("/hostel/inventory/", { params: filters });
      return res.data;
    },
  });
}

export function useCreateInventoryItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: any) => {
      const res = await http.post<HostelInventoryItem>("/hostel/inventory/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "inventory"] });
      notifySuccess("Inventory item saved.");
    },
    onError: (e) => notifyError(e),
  });
}

export function useInventoryAudits(item_id?: number) {
  return useQuery({
    queryKey: keys.inventoryAudits({ item_id }),
    queryFn: async () => {
      const res = await http.get<InventoryAuditLog[]>("/hostel/inventory/audits/", { params: { item_id } });
      return res.data;
    },
  });
}

export function useStaffAssignments(hostel_id?: number) {
  return useQuery({
    queryKey: keys.staff({ hostel_id }),
    queryFn: async () => {
      const res = await http.get<StaffAssignment[]>("/hostel/staff/", { params: { hostel_id } });
      return res.data;
    },
  });
}

export function useCreateStaffAssignment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: any) => {
      const res = await http.post<StaffAssignment>("/hostel/staff/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "staff"] });
      notifySuccess("Staff assignment recorded.");
    },
    onError: (e) => notifyError(e),
  });
}

// -- Security Guard Shifts --
export function useSecurityShifts(filters?: { hostel_id?: number; shift_date?: string }) {
  return useQuery({
    queryKey: keys.security(filters),
    queryFn: async () => {
      const res = await http.get<SecurityGuardShift[]>("/hostel/security-shifts/", { params: filters });
      return res.data;
    },
  });
}

export function useCreateSecurityShift() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: any) => {
      const res = await http.post<SecurityGuardShift>("/hostel/security-shifts/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "security"] });
      notifySuccess("Security shift roster saved.");
    },
    onError: (e) => notifyError(e),
  });
}

// -- Notices --
export function useNotices(hostel_id?: number) {
  return useQuery({
    queryKey: keys.notices({ hostel_id }),
    queryFn: async () => {
      const res = await http.get<HostelNotice[]>("/hostel/notices/", { params: { hostel_id } });
      return res.data;
    },
  });
}

export function usePublishNotice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: any) => {
      const res = await http.post<HostelNotice>("/hostel/notices/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "notices"] });
      notifySuccess("Hostel notice published.");
    },
    onError: (e) => notifyError(e),
  });
}

// -- Notifications --
export function useNotifications() {
  return useQuery({
    queryKey: keys.notifications(),
    queryFn: async () => {
      const res = await http.get<NotificationRecord[]>("/hostel/notifications/");
      return res.data;
    },
  });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await http.post(`/hostel/notifications/${id}/read/`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "notifications"] });
    },
  });
}

// -- Reports --
export function useOperationalReport(report_type: string, hostel_id?: number) {
  return useQuery({
    queryKey: keys.reports({ report_type, hostel_id }),
    queryFn: async () => {
      const res = await http.get<OperationalReport>("/hostel/reports/", { params: { report_type, hostel_id } });
      return res.data;
    },
  });
}
