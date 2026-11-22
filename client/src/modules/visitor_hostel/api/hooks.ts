import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type { Booking, InventoryItem, Page, Replenishment, Room } from "./types";

const BASE = "/visitorhostel";

export const useBookings = (status?: string) => useQuery({
  queryKey: ["visitor-hostel", "bookings", status],
  queryFn: async () => (await http.get<Page<Booking> | Booking[]>(
    `${BASE}/bookings`, { params: status ? { status } : undefined },
  )).data,
});

export const useCreateBooking = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<Booking>(`${BASE}/bookings`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["visitor-hostel"] }),
  });
};

export const useReviewBooking = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, outcome, reason }: {
      id: number; outcome: "forward" | "reject"; reason: string;
    }) => (await http.post<Booking>(
      `${BASE}/bookings/${id}/review`, { outcome, reason },
    )).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["visitor-hostel"] }),
  });
};

export const useRooms = () => useQuery({
  queryKey: ["visitor-hostel", "rooms"],
  queryFn: async () => (await http.get<Room[]>(`${BASE}/rooms`)).data,
});

export const useAllotRoom = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, room_id, occupancy }: {
      id: number; room_id: number; occupancy: "single" | "double";
    }) => (await http.post<Booking>(
      `${BASE}/bookings/${id}/allot`,
      { rooms: [{ room_id, occupancy }] },
    )).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["visitor-hostel"] }),
  });
};

export const useInventory = () => useQuery({
  queryKey: ["visitor-hostel", "inventory"],
  queryFn: async () =>
    (await http.get<InventoryItem[]>(`${BASE}/inventory`)).data,
});

export const useReplenishments = () => useQuery({
  queryKey: ["visitor-hostel", "replenishments"],
  queryFn: async () =>
    (await http.get<Replenishment[]>(`${BASE}/replenishments`)).data,
});

export const useApproveReplenishment = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, approved }: { id: number; approved: boolean }) =>
      (await http.post<Replenishment>(
        `${BASE}/replenishments/${id}/approve`, { approved },
      )).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["visitor-hostel"] }),
  });
};
