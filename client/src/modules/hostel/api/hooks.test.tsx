import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { useDashboardStats, useHostels } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("Hostel Management hooks", () => {
  it("fetches list of hostels successfully", async () => {
    const mockHostels = {
      results: [
        { id: 1, name: "Aryabhatta Hostel", code: "BH-1", capacity: 100, is_active: true },
      ],
      next: null,
      previous: null,
    };
    vi.spyOn(http, "get").mockResolvedValue({ data: mockHostels });

    const { result } = renderHook(() => useHostels(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.results).toHaveLength(1);
    expect(result.current.data?.results?.[0]?.code).toBe("BH-1");
    expect(http.get).toHaveBeenCalledWith("/hostel/hostels/", { params: undefined });
  });

  it("fetches dashboard stats successfully", async () => {
    const mockStats = {
      is_admin: true,
      hostels_count: 3,
      total_capacity: 500,
      total_occupancy: 420,
      open_complaints: 4,
    };
    vi.spyOn(http, "get").mockResolvedValue({ data: mockStats });

    const { result } = renderHook(() => useDashboardStats(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.is_admin).toBe(true);
    expect(result.current.data?.total_capacity).toBe(500);
    expect(http.get).toHaveBeenCalledWith("/hostel/dashboard/stats/");
  });
});
