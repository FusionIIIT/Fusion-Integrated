import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  Hostel,
  Room,
  AccommodationRequest,
  RoomAssignment,
  AttendanceRecord,
  LeaveRequest,
  Complaint,
  GuestBooking,
  ExtendedStayRequest,
  FineRecord,
  InventoryItem,
  GuardShift,
  Notice,
} from "./types";

export function useHostels() {
  return useQuery({
    queryKey: ["hm", "hostels"],
    queryFn: () => http<Hostel[]>("/api/v1/hm/hostels"),
  });
}

export function useRooms(hostelId?: number) {
  return useQuery({
    queryKey: ["hm", "rooms", hostelId],
    queryFn: () => http<Room[]>(hostelId ? `/api/v1/hm/rooms?hostel_id=${hostelId}` : "/api/v1/hm/rooms"),
  });
}

export function useAccommodationRequests() {
  return useQuery({
    queryKey: ["hm", "accommodation-requests"],
    queryFn: () => http<AccommodationRequest[]>("/api/v1/hm/accommodation-requests"),
  });
}

export function useSubmitAccommodationRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<AccommodationRequest>) =>
      http<AccommodationRequest>("/api/v1/hm/accommodation-requests", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["hm", "accommodation-requests"] });
    },
  });
}

export function useAttendanceRecords() {
  return useQuery({
    queryKey: ["hm", "attendance"],
    queryFn: () => http<AttendanceRecord[]>("/api/v1/hm/attendance"),
  });
}

export function useLeaveRequests() {
  return useQuery({
    queryKey: ["hm", "leave-requests"],
    queryFn: () => http<LeaveRequest[]>("/api/v1/hm/leave-requests"),
  });
}

export function useSubmitLeaveRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<LeaveRequest>) =>
      http<LeaveRequest>("/api/v1/hm/leave-requests", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["hm", "leave-requests"] });
    },
  });
}

export function useComplaints() {
  return useQuery({
    queryKey: ["hm", "complaints"],
    queryFn: () => http<Complaint[]>("/api/v1/hm/complaints"),
  });
}

export function useSubmitComplaint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Complaint>) =>
      http<Complaint>("/api/v1/hm/complaints", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["hm", "complaints"] });
    },
  });
}

export function useGuestBookings() {
  return useQuery({
    queryKey: ["hm", "guest-bookings"],
    queryFn: () => http<GuestBooking[]>("/api/v1/hm/guest-bookings"),
  });
}

export function useExtendedStays() {
  return useQuery({
    queryKey: ["hm", "extended-stays"],
    queryFn: () => http<ExtendedStayRequest[]>("/api/v1/hm/extended-stays"),
  });
}

export function useFines() {
  return useQuery({
    queryKey: ["hm", "fines"],
    queryFn: () => http<FineRecord[]>("/api/v1/hm/fines"),
  });
}

export function useInventoryItems() {
  return useQuery({
    queryKey: ["hm", "inventory"],
    queryFn: () => http<InventoryItem[]>("/api/v1/hm/inventory"),
  });
}

export function useGuardShifts() {
  return useQuery({
    queryKey: ["hm", "guard-shifts"],
    queryFn: () => http<GuardShift[]>("/api/v1/hm/guard-shifts"),
  });
}

export function useNotices() {
  return useQuery({
    queryKey: ["hm", "notices"],
    queryFn: () => http<Notice[]>("/api/v1/hm/notices"),
  });
}
