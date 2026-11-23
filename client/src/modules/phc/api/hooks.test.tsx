import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { useDoctorAvailability, useSubmitClaim } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

afterEach(() => vi.restoreAllMocks());

describe("PHC API hooks", () => {
  it("reads published availability through the shared HTTP client", async () => {
    const get = vi.spyOn(http, "get").mockResolvedValue({ data: [] } as never);
    const { result } = renderHook(() => useDoctorAvailability(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(get).toHaveBeenCalledWith("/phc/doctor-availability");
  });

  it("submits reimbursement claims through the shared HTTP client", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 3 } } as never);
    const { result } = renderHook(() => useSubmitClaim(), { wrapper });
    const body = { prescription_id: 7, claim_amount: "200.00", expense_date: "2026-11-20" };

    result.current.mutate(body);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(post).toHaveBeenCalledWith("/phc/reimbursements", body);
  });
});
