import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { useApplyLeave, useMyBalances } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("ELM API hooks", () => {
  it("useApplyLeave posts to /api/v1/elm/leaves", async () => {
    const mockLeave = {
      id: 1,
      category: "CL",
      status: "awaiting_unit_head",
      start_date: "2026-11-02",
      end_date: "2026-11-02",
      days_counted: 1,
    };
    vi.spyOn(http, "post").mockResolvedValue({ data: mockLeave });

    const { result } = renderHook(() => useApplyLeave(), { wrapper });
    result.current.mutate({
      category: "CL",
      start_date: "2026-11-02",
      end_date: "2026-11-02",
      half: "full",
      purpose: "Doctor appointment",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/api/v1/elm/leaves", {
      category: "CL",
      start_date: "2026-11-02",
      end_date: "2026-11-02",
      half: "full",
      purpose: "Doctor appointment",
    });
    expect(result.current.data).toEqual(mockLeave);
  });

  it("useMyBalances fetches from /api/v1/elm/balances/my", async () => {
    const mockBalances = {
      results: [
        { id: 1, category: "CL", available: 8, credited: 8, used: 0, carried_forward: 0 },
      ],
    };
    vi.spyOn(http, "get").mockResolvedValue({ data: mockBalances });

    const { result } = renderHook(() => useMyBalances(2026), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/api/v1/elm/balances/my", { params: { year: 2026 } });
    expect(result.current.data?.results).toHaveLength(1);
  });
});
