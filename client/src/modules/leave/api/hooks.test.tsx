import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { errorMessage } from "../../../lib/http";
import {
  useApplyLeave,
  useLeaveBalances,
  useLeaveTypes,
  useWithdrawRequest,
} from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("Leave API Queries and Mutations", () => {
  it("fetches active leave types", async () => {
    const mockTypes = [
      { code: "CL", name: "Casual Leave", allows_half_day: true, requires_substitute: false },
      { code: "EL", name: "Earned Leave", allows_half_day: false, requires_substitute: true },
    ];
    vi.spyOn(http, "get").mockResolvedValueOnce({ data: mockTypes });

    const { result } = renderHook(() => useLeaveTypes(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockTypes);
    expect(http.get).toHaveBeenCalledWith("/leave/types/");
  });

  it("fetches user balances with year filter", async () => {
    const mockBalances = [
      { id: 1, year: 2026, credited_days: "8.0", used_days: "0.0", available_days: "8.0" },
    ];
    vi.spyOn(http, "get").mockResolvedValueOnce({ data: mockBalances });

    const { result } = renderHook(() => useLeaveBalances(2026), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockBalances);
    expect(http.get).toHaveBeenCalledWith("/leave/balances/", { params: { year: 2026 } });
  });

  it("submits leave application successfully", async () => {
    const payload = {
      leave_type_code: "CL",
      start_date: "2026-10-15",
      end_date: "2026-10-16",
      reason: "Family function",
    };
    const mockCreated = { id: 101, application_number: "LEAVE-2026-101", status: "awaiting_unit_head" };
    vi.spyOn(http, "post").mockResolvedValueOnce({ data: mockCreated });

    const { result } = renderHook(() => useApplyLeave(), { wrapper });
    result.current.mutate(payload);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockCreated);
    expect(http.post).toHaveBeenCalledWith("/leave/applications/", payload);
  });

  it("handles validation and conflict error responses properly", async () => {
    const payload = {
      leave_type_code: "CL",
      start_date: "2026-10-20",
      end_date: "2026-10-10",
      reason: "Inverted dates",
    };
    const envelope = {
      error: { code: "bad_request", message: "End date must be greater than or equal to start date." },
    };
    vi.spyOn(http, "post").mockRejectedValueOnce({
      response: { status: 400, data: envelope },
    });

    const { result } = renderHook(() => useApplyLeave(), { wrapper });
    result.current.mutate(payload);

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(errorMessage(result.current.error)).toBe(
      "End date must be greater than or equal to start date."
    );
  });

  it("withdraws an eligible pending application", async () => {
    const mockWithdrawn = { id: 101, status: "withdrawn" };
    vi.spyOn(http, "post").mockResolvedValueOnce({ data: mockWithdrawn });

    const { result } = renderHook(() => useWithdrawRequest(), { wrapper });
    result.current.mutate({ id: 101, payload: { remarks: "Changed plans" } });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/leave/requests/101/withdraw/", { remarks: "Changed plans" });
  });
});
