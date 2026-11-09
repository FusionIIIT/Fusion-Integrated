/** React Query hooks for Visitors Hostel (VH) API access. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  Bill,
  Booking,
  BookingModification,
  CaretakerReport,
  InChargeReport,
  InventoryItem,
  InventoryReplenishment,
  MealBooking,
  PrintableBookingSlip,
  Room,
  Tariff,
  VisitorCategory,
} from "./types";

const KEY = "vh";

export const vhKeys = {
  all: [KEY] as const,
  categories: () => [KEY, "categories"] as const,
  rooms: (params?: Record<string, unknown>) => [KEY, "rooms", params] as const,
  availability: (checkIn?: string, checkOut?: string) => [KEY, "availability", checkIn, checkOut] as const,
  tariffs: () => [KEY, "tariffs"] as const,
  bookings: (params?: Record<string, unknown>) => [KEY, "bookings", params] as const,
  booking: (id: number) => [KEY, "booking", id] as const,
  printable: (id: number) => [KEY, "printable", id] as const,
  meals: (bookingId?: number) => [KEY, "meals", bookingId] as const,
  bills: () => [KEY, "bills"] as const,
  inventory: () => [KEY, "inventory"] as const,
  inventoryAlerts: () => [KEY, "inventory", "alerts"] as const,
  replenishments: () => [KEY, "replenishments"] as const,
  inchargeReport: () => [KEY, "reports", "incharge"] as const,
  caretakerReport: () => [KEY, "reports", "caretaker"] as const,
};

export function useVisitorCategories() {
  return useQuery({
    queryKey: vhKeys.categories(),
    queryFn: async () => {
      const res = await http.get<VisitorCategory[]>("/vh/categories/");
      return res.data;
    },
  });
}

export function useRooms(params?: { status?: string; room_type?: string }) {
  return useQuery({
    queryKey: vhKeys.rooms(params),
    queryFn: async () => {
      const res = await http.get<Room[]>("/vh/rooms/", { params });
      return res.data;
    },
  });
}

export function useRoomAvailability(checkIn?: string, checkOut?: string) {
  return useQuery({
    queryKey: vhKeys.availability(checkIn, checkOut),
    queryFn: async () => {
      if (!checkIn || !checkOut) return [];
      const res = await http.get<Room[]>("/vh/rooms/availability/", {
        params: { check_in: checkIn, check_out: checkOut },
      });
      return res.data;
    },
    enabled: Boolean(checkIn && checkOut),
  });
}

export function useTariffs() {
  return useQuery({
    queryKey: vhKeys.tariffs(),
    queryFn: async () => {
      const res = await http.get<Tariff[]>("/vh/tariffs/");
      return res.data;
    },
  });
}

export function useBookings(params?: { indenter_id?: number; status?: string; is_offline?: boolean }) {
  return useQuery({
    queryKey: vhKeys.bookings(params),
    queryFn: async () => {
      const res = await http.get<Booking[]>("/vh/bookings/", { params });
      return res.data;
    },
  });
}

export function useBooking(id: number) {
  return useQuery({
    queryKey: vhKeys.booking(id),
    queryFn: async () => {
      const res = await http.get<Booking>(`/vh/bookings/${id}/`);
      return res.data;
    },
    enabled: Boolean(id),
  });
}

export function usePrintableBooking(id: number) {
  return useQuery({
    queryKey: vhKeys.printable(id),
    queryFn: async () => {
      const res = await http.get<PrintableBookingSlip>(`/vh/bookings/${id}/printable/`);
      return res.data;
    },
    enabled: Boolean(id),
  });
}

export function useCreateBooking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Booking>) => {
      const res = await http.post<Booking>("/vh/bookings/", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.bookings() });
    },
  });
}

export function useForwardBooking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remarks }: { id: number; remarks?: string }) => {
      const res = await http.post<Booking>(`/vh/bookings/${id}/forward/`, { remarks });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.bookings() });
    },
  });
}

export function useApproveBooking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remarks }: { id: number; remarks?: string }) => {
      const res = await http.post<Booking>(`/vh/bookings/${id}/approve/`, { remarks });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.bookings() });
    },
  });
}

export function useRejectBooking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remarks }: { id: number; remarks?: string }) => {
      const res = await http.post<Booking>(`/vh/bookings/${id}/reject/`, { remarks });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.bookings() });
    },
  });
}

export function useAllotRoom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, room_ids }: { id: number; room_ids: number[] }) => {
      const res = await http.post<{ message: string; booking: Booking }>(
        `/vh/bookings/${id}/allot_room/`,
        { room_ids },
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.bookings() });
      qc.invalidateQueries({ queryKey: vhKeys.rooms() });
    },
  });
}

export function useCheckIn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await http.post<Booking>(`/vh/bookings/${id}/check_in/`);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.bookings() });
    },
  });
}

export function useCheckOut() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await http.post<{ message: string; booking: Booking; bill: Bill }>(
        `/vh/bookings/${id}/check_out/`,
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.bookings() });
      qc.invalidateQueries({ queryKey: vhKeys.bills() });
      qc.invalidateQueries({ queryKey: vhKeys.rooms() });
    },
  });
}

export function useRequestCancellation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason: string }) => {
      const res = await http.post<{ message: string; booking: Booking; applicable_cancellation_charge: string }>(
        `/vh/bookings/${id}/request_cancellation/`,
        { reason },
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.bookings() });
    },
  });
}

export function useConfirmCancellation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await http.post<{ message: string; booking: Booking; bill: Bill }>(
        `/vh/bookings/${id}/confirm_cancellation/`,
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.bookings() });
      qc.invalidateQueries({ queryKey: vhKeys.bills() });
    },
  });
}

export function useCreateModification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<BookingModification>) => {
      const res = await http.post<BookingModification>("/vh/modifications/", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.bookings() });
    },
  });
}

export function useConfirmModification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remarks }: { id: number; remarks?: string }) => {
      const res = await http.post<BookingModification>(`/vh/modifications/${id}/confirm/`, { remarks });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.bookings() });
    },
  });
}

export function useMealBookings(bookingId?: number) {
  return useQuery({
    queryKey: vhKeys.meals(bookingId),
    queryFn: async () => {
      const res = await http.get<MealBooking[]>("/vh/meals/", {
        params: bookingId ? { booking: bookingId } : undefined,
      });
      return res.data;
    },
  });
}

export function useCreateMealBooking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<MealBooking>) => {
      const res = await http.post<MealBooking>("/vh/meals/", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.meals() });
      qc.invalidateQueries({ queryKey: vhKeys.bookings() });
    },
  });
}

export function useBills() {
  return useQuery({
    queryKey: vhKeys.bills(),
    queryFn: async () => {
      const res = await http.get<Bill[]>("/vh/bills/");
      return res.data;
    },
  });
}

export function useSettleBill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, notes }: { id: number; notes: string }) => {
      const res = await http.post<Bill>(`/vh/bills/${id}/settle/`, {
        guest_verification_notes: notes,
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.bills() });
      qc.invalidateQueries({ queryKey: vhKeys.bookings() });
    },
  });
}

export function useInventoryItems() {
  return useQuery({
    queryKey: vhKeys.inventory(),
    queryFn: async () => {
      const res = await http.get<InventoryItem[]>("/vh/inventory/");
      return res.data;
    },
  });
}

export function useInventoryAlerts() {
  return useQuery({
    queryKey: vhKeys.inventoryAlerts(),
    queryFn: async () => {
      const res = await http.get<InventoryItem[]>("/vh/inventory/alerts/");
      return res.data;
    },
  });
}

export function useRequestReplenishment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ itemId, quantity, remarks }: { itemId: number; quantity: number; remarks: string }) => {
      const res = await http.post<InventoryReplenishment>(
        `/vh/inventory/${itemId}/request_replenishment/`,
        { quantity_requested: quantity, remarks },
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.replenishments() });
      qc.invalidateQueries({ queryKey: vhKeys.inventory() });
    },
  });
}

export function useReplenishments() {
  return useQuery({
    queryKey: vhKeys.replenishments(),
    queryFn: async () => {
      const res = await http.get<InventoryReplenishment[]>("/vh/replenishments/");
      return res.data;
    },
  });
}

export function useApproveReplenishment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await http.post<InventoryReplenishment>(`/vh/replenishments/${id}/approve/`);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.replenishments() });
      qc.invalidateQueries({ queryKey: vhKeys.inventory() });
    },
  });
}

export function useRejectReplenishment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await http.post<InventoryReplenishment>(`/vh/replenishments/${id}/reject/`);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.replenishments() });
    },
  });
}

export function useInChargeReport() {
  return useQuery({
    queryKey: vhKeys.inchargeReport(),
    queryFn: async () => {
      const res = await http.get<InChargeReport>("/vh/reports/incharge/");
      return res.data;
    },
  });
}

export function useCaretakerReport() {
  return useQuery({
    queryKey: vhKeys.caretakerReport(),
    queryFn: async () => {
      const res = await http.get<CaretakerReport>("/vh/reports/caretaker/");
      return res.data;
    },
  });
}

export function useScanAlerts() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await http.post<{ message: string; no_shows_detected: number; overstays_detected: number; inventory_alerts_active: number }>("/vh/alerts/scan/");
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: vhKeys.caretakerReport() });
      qc.invalidateQueries({ queryKey: vhKeys.inchargeReport() });
    },
  });
}

