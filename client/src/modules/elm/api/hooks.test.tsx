import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { useApplyLeave, useBalances } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("ELM api hooks", () => {
  it("fetches leave balances", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: [{ id: 1, user_id: 101, leave_type: "CL", balance: 8, updated_at: "2026-10-26" }],
    });

    const { result } = renderHook(() => useBalances(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0]?.leave_type).toBe("CL");
  });

  it("submits leave application", async () => {
    vi.spyOn(http, "post").mockResolvedValue({
      data: {
        id: 99,
        user_id: 101,
        applicant_name: "Test User",
        leave_type: "CL",
        start_date: "2026-10-27",
        end_date: "2026-10-28",
        reason: "Vacation",
        status: "PENDING",
      },
    });

    const { result } = renderHook(() => useApplyLeave(), { wrapper });
    result.current.mutate({
      leave_type: "CL",
      start_date: "2026-10-27",
      end_date: "2026-10-28",
      reason: "Vacation",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe(99);
  });
});
