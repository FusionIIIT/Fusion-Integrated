import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import {
  useAllotRoom,
  useApproveBooking,
  useBookings,
  useCheckIn,
  useCheckOut,
  useConfirmCancellation,
  useCreateBooking,
  useCreateMealBooking,
  useForwardBooking,
  useRejectBooking,
  useSettleBill,
  useVisitorCategories,
} from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("Visitor Hostel React Query Hooks", () => {
  it("fetches visitor categories", async () => {
    const mockCategories = [
      { id: 1, code: "A", name: "Category A", description: "Institute Guests" },
    ];
    vi.spyOn(http, "get").mockResolvedValue({ data: mockCategories });

    const { result } = renderHook(() => useVisitorCategories(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockCategories);
    expect(http.get).toHaveBeenCalledWith("/vh/categories/");
  });

  it("fetches bookings with query parameters", async () => {
    const mockBookings = [
      { id: 101, booking_reference: "VH-2026-0001", status: "PENDING" },
    ];
    vi.spyOn(http, "get").mockResolvedValue({ data: mockBookings });

    const { result } = renderHook(() => useBookings({ status: "PENDING" }), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockBookings);
    expect(http.get).toHaveBeenCalledWith("/vh/bookings/", {
      params: { status: "PENDING" },
    });
  });

  it("creates a new booking via mutation", async () => {
    const createdBooking = {
      id: 102,
      booking_reference: "VH-2026-0002",
      visitor_name: "Dr. Alice",
      status: "PENDING",
    };
    vi.spyOn(http, "post").mockResolvedValue({ data: createdBooking });

    const { result } = renderHook(() => useCreateBooking(), { wrapper });
    result.current.mutate({ visitor_name: "Dr. Alice" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(createdBooking);
    expect(http.post).toHaveBeenCalledWith("/vh/bookings/", { visitor_name: "Dr. Alice" });
  });

  it("forwards booking to incharge", async () => {
    const forwardedBooking = { id: 102, status: "FORWARDED" };
    vi.spyOn(http, "post").mockResolvedValue({ data: forwardedBooking });

    const { result } = renderHook(() => useForwardBooking(), { wrapper });
    result.current.mutate({ id: 102, remarks: "Checked availability" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/vh/bookings/102/forward/", {
      remarks: "Checked availability",
    });
  });

  it("approves booking by incharge", async () => {
    const approvedBooking = { id: 102, status: "APPROVED" };
    vi.spyOn(http, "post").mockResolvedValue({ data: approvedBooking });

    const { result } = renderHook(() => useApproveBooking(), { wrapper });
    result.current.mutate({ id: 102, remarks: "Sanctioned" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/vh/bookings/102/approve/", {
      remarks: "Sanctioned",
    });
  });

  it("rejects booking with remarks", async () => {
    const rejectedBooking = { id: 102, status: "REJECTED" };
    vi.spyOn(http, "post").mockResolvedValue({ data: rejectedBooking });

    const { result } = renderHook(() => useRejectBooking(), { wrapper });
    result.current.mutate({ id: 102, remarks: "No capacity" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/vh/bookings/102/reject/", {
      remarks: "No capacity",
    });
  });

  it("allots room to booking", async () => {
    const allotmentResponse = { message: "Rooms allotted", booking: { id: 102, status: "ROOM_ALLOTTED" } };
    vi.spyOn(http, "post").mockResolvedValue({ data: allotmentResponse });

    const { result } = renderHook(() => useAllotRoom(), { wrapper });
    result.current.mutate({ id: 102, room_ids: [1, 2] });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/vh/bookings/102/allot_room/", {
      room_ids: [1, 2],
    });
  });

  it("checks in guest", async () => {
    const checkedInBooking = { id: 102, status: "CHECKED_IN" };
    vi.spyOn(http, "post").mockResolvedValue({ data: checkedInBooking });

    const { result } = renderHook(() => useCheckIn(), { wrapper });
    result.current.mutate(102);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/vh/bookings/102/check_in/");
  });

  it("checks out guest and computes bill", async () => {
    const checkOutResponse = {
      message: "Checked out",
      booking: { id: 102, status: "CHECKED_OUT" },
      bill: { id: 50, total_amount: "3000.00" },
    };
    vi.spyOn(http, "post").mockResolvedValue({ data: checkOutResponse });

    const { result } = renderHook(() => useCheckOut(), { wrapper });
    result.current.mutate(102);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/vh/bookings/102/check_out/");
  });

  it("confirms booking cancellation", async () => {
    const cancelResponse = {
      message: "Cancelled",
      booking: { id: 102, status: "CANCELLED" },
      bill: { id: 51, total_amount: "500.00" },
    };
    vi.spyOn(http, "post").mockResolvedValue({ data: cancelResponse });

    const { result } = renderHook(() => useConfirmCancellation(), { wrapper });
    result.current.mutate(102);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/vh/bookings/102/confirm_cancellation/");
  });

  it("creates meal booking for residing guest", async () => {
    const mealBooking = { id: 201, booking: 102, meal_type: "LUNCH", total_amount: "150.00" };
    vi.spyOn(http, "post").mockResolvedValue({ data: mealBooking });

    const { result } = renderHook(() => useCreateMealBooking(), { wrapper });
    result.current.mutate({ booking: 102, meal_type: "LUNCH", number_of_persons: 1 });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/vh/meals/", {
      booking: 102,
      meal_type: "LUNCH",
      number_of_persons: 1,
    });
  });

  it("settles hostel bill", async () => {
    const settledBill = { id: 50, is_settled: true };
    vi.spyOn(http, "post").mockResolvedValue({ data: settledBill });

    const { result } = renderHook(() => useSettleBill(), { wrapper });
    result.current.mutate({ id: 50, notes: "Cash verified" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/vh/bills/50/settle/", {
      guest_verification_notes: "Cash verified",
    });
  });
});

