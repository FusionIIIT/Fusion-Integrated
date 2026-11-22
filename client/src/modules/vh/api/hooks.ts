// TanStack Query data access hooks for the VHMS module.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  AllotRoomsPayload,
  ArrivalsDeparturesReport,
  Bill,
  Booking,
  BookingSummaryReport,
  BookMealPayload,
  CancelBookingPayload,
  CategoryOccupancyItem,
  CheckInPayload,
  CheckOutPayload,
  CreateBookingPayload,
  CreateOfflineBookingPayload,
  DailyOccupancyReport,
  DecideBookingPayload,
  InventoryItem,
  InventoryReplenishment,
  InventoryUsageItem,
  MealBooking,
  ModifyBookingPayload,
  PendingApprovalsReport,
  ReassignRolePayload,
  ReplenishApprovePayload,
  ReplenishRequestPayload,
  RevenueSummaryReport,
  Room,
  RouteBookingPayload,
  SettleBillPayload,
  StayExceptionLog,
  TariffConfig,
} from "./types";

const KEY = "vh";

export const keys = {
  bookings: (filters?: unknown) => [KEY, "bookings", filters] as const,
  booking: (id: number) => [KEY, "booking", id] as const,
  meals: (bookingId: number) => [KEY, "meals", bookingId] as const,
  bill: (bookingId: number) => [KEY, "bill", bookingId] as const,
  roomAvailability: (params: unknown) => [KEY, "room-availability", params] as const,
  tariffs: (params?: unknown) => [KEY, "tariffs", params] as const,
  inventory: (params?: unknown) => [KEY, "inventory", params] as const,
  replenishments: (params?: unknown) => [KEY, "replenishments", params] as const,
  caretakerReport: (type: string, date?: string) => [KEY, "caretaker-report", type, date] as const,
  inchargeReport: (type: string) => [KEY, "incharge-report", type] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Bookings -----------------------------------------------------------------

export function useBookings(filters?: { status?: string; is_offline?: boolean }) {
  return useQuery({
    queryKey: keys.bookings(filters),
    queryFn: async () => (await http.get<Booking[]>("/vh/bookings/", { params: filters })).data,
    staleTime: 15_000,
  });
}

export function useBooking(id: number | undefined) {
  return useQuery({
    queryKey: keys.booking(id ?? 0),
    queryFn: async () => (await http.get<Booking>(`/vh/bookings/${id}/`)).data,
    enabled: typeof id === "number" && id > 0,
  });
}

export function useCreateBooking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateBookingPayload) =>
      (await http.post<Booking>("/vh/bookings/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCreateOfflineBooking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateOfflineBookingPayload) =>
      (await http.post<Booking>("/vh/bookings/offline/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useModifyBooking(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ModifyBookingPayload) =>
      (await http.post<Booking>(`/vh/bookings/${id}/modify/`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRouteBooking(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: RouteBookingPayload) =>
      (await http.post<Booking>(`/vh/bookings/${id}/route/`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDecideBooking(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: DecideBookingPayload) =>
      (await http.post<Booking>(`/vh/bookings/${id}/decide/`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCancelBooking(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CancelBookingPayload) =>
      (await http.post<Booking>(`/vh/bookings/${id}/cancel/`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useConfirmCancellation(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      (await http.post<Booking>(`/vh/bookings/${id}/confirm-cancellation/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAllotRooms(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AllotRoomsPayload) =>
      (await http.post<Booking>(`/vh/bookings/${id}/allot-rooms/`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCheckIn(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload?: CheckInPayload) =>
      (await http.post<Booking>(`/vh/bookings/${id}/checkin/`, payload ?? {})).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCheckOut(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CheckOutPayload) =>
      (await http.post<Booking>(`/vh/bookings/${id}/checkout/`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Meals --------------------------------------------------------------------

export function useBookingMeals(bookingId: number | undefined) {
  return useQuery({
    queryKey: keys.meals(bookingId ?? 0),
    queryFn: async () => (await http.get<MealBooking[]>(`/vh/bookings/${bookingId}/meals/`)).data,
    enabled: typeof bookingId === "number" && bookingId > 0,
  });
}

export function useBookMeal(bookingId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: BookMealPayload) =>
      (await http.post<MealBooking>(`/vh/bookings/${bookingId}/meals/`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Billing ------------------------------------------------------------------

export function useBookingBill(bookingId: number | undefined) {
  return useQuery({
    queryKey: keys.bill(bookingId ?? 0),
    queryFn: async () => (await http.post<Bill>(`/vh/bookings/${bookingId}/bill/`)).data,
    enabled: typeof bookingId === "number" && bookingId > 0,
  });
}

export function useSettleBill(billId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SettleBillPayload) =>
      (await http.post<{ id: number; amount_paid: string }>(`/vh/bills/${billId}/settle/`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Rooms & Availability -----------------------------------------------------

export function useRoomAvailability(params: {
  arrival_date?: string;
  departure_date?: string;
  room_type?: string;
}) {
  return useQuery({
    queryKey: keys.roomAvailability(params),
    queryFn: async () => (await http.get<Room[]>("/vh/rooms/availability/", { params })).data,
    enabled: Boolean(params.arrival_date && params.departure_date),
  });
}

// -- Tariffs ------------------------------------------------------------------

export function useTariffs(params?: { category?: string; room_type?: string }) {
  return useQuery({
    queryKey: keys.tariffs(params),
    queryFn: async () => (await http.get<TariffConfig[]>("/vh/tariffs/", { params })).data,
  });
}

export function useCreateTariff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<TariffConfig>) =>
      (await http.post<TariffConfig>("/vh/tariffs/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Inventory ----------------------------------------------------------------

export function useInventory(params?: { category?: string }) {
  return useQuery({
    queryKey: keys.inventory(params),
    queryFn: async () => (await http.get<InventoryItem[]>("/vh/inventory/", { params })).data,
  });
}

export function useSaveInventoryItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<InventoryItem>) =>
      (await http.post<InventoryItem>("/vh/inventory/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRequestReplenishment(itemId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ReplenishRequestPayload) =>
      (await http.post<InventoryReplenishment>(`/vh/inventory/${itemId}/replenish/`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useApproveReplenishment(replenishId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ReplenishApprovePayload) =>
      (await http.post<InventoryReplenishment>(
        `/vh/inventory/replenishments/${replenishId}/approve/`,
        payload
      )).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Reports ------------------------------------------------------------------

export function useDailyOccupancyReport(date?: string) {
  return useQuery({
    queryKey: keys.caretakerReport("occupancy", date),
    queryFn: async () =>
      (await http.get<DailyOccupancyReport>("/vh/reports/caretaker/", {
        params: { report_type: "occupancy", date },
      })).data,
  });
}

export function useArrivalsDeparturesReport(date?: string) {
  return useQuery({
    queryKey: keys.caretakerReport("arrivals_departures", date),
    queryFn: async () =>
      (await http.get<ArrivalsDeparturesReport>("/vh/reports/caretaker/", {
        params: { report_type: "arrivals_departures", date },
      })).data,
  });
}

export function usePendingApprovalsReport() {
  return useQuery({
    queryKey: keys.caretakerReport("pending_approvals"),
    queryFn: async () =>
      (await http.get<PendingApprovalsReport>("/vh/reports/caretaker/", {
        params: { report_type: "pending_approvals" },
      })).data,
  });
}

export function useStayExceptionsReport() {
  return useQuery({
    queryKey: keys.caretakerReport("exceptions"),
    queryFn: async () =>
      (await http.get<StayExceptionLog[]>("/vh/reports/caretaker/", {
        params: { report_type: "exceptions" },
      })).data,
  });
}

export function useBookingSummaryReport() {
  return useQuery({
    queryKey: keys.inchargeReport("summary"),
    queryFn: async () =>
      (await http.get<BookingSummaryReport>("/vh/reports/incharge/", {
        params: { report_type: "summary" },
      })).data,
  });
}

export function useCategoryOccupancyReport() {
  return useQuery({
    queryKey: keys.inchargeReport("category_occupancy"),
    queryFn: async () =>
      (await http.get<CategoryOccupancyItem[]>("/vh/reports/incharge/", {
        params: { report_type: "category_occupancy" },
      })).data,
  });
}

export function useRevenueSummaryReport() {
  return useQuery({
    queryKey: keys.inchargeReport("revenue"),
    queryFn: async () =>
      (await http.get<RevenueSummaryReport>("/vh/reports/incharge/", {
        params: { report_type: "revenue" },
      })).data,
  });
}

export function useInventoryUsageReport() {
  return useQuery({
    queryKey: keys.inchargeReport("inventory"),
    queryFn: async () =>
      (await http.get<InventoryUsageItem[]>("/vh/reports/incharge/", {
        params: { report_type: "inventory" },
      })).data,
  });
}

// -- Role Reassignment --------------------------------------------------------

export function useReassignRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ReassignRolePayload) =>
      (await http.post<{ id: number; role_name: string; user_id: number }>("/vh/roles/reassign/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}
