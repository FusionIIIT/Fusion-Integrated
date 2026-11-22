import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { useDashboardMetrics, useUsers } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("superadmin hooks", () => {
  it("fetches dashboard metrics", async () => {
    const mockMetrics = {
      total_users: 100,
      active_users: 95,
      deactivated_users: 5,
      archived_reversible_users: 0,
      archived_permanent_users: 0,
    };
    vi.spyOn(http, "get").mockResolvedValue({ data: mockMetrics });

    const { result } = renderHook(() => useDashboardMetrics(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.total_users).toBe(100);
    expect(http.get).toHaveBeenCalledWith("/superadmin/dashboard/");
  });

  it("fetches users list with search filter", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [] });

    const { result } = renderHook(() => useUsers({ search: "24BCS" }), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/superadmin/users/", {
      params: { search: "24BCS", user_type: undefined, status: undefined },
    });
  });
});
