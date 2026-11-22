import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useClaimTransition, usePatientSearch, useReport, useSubmitClaim } from "./hooks";

const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }));
vi.mock("../../../lib/http", async (orig) => ({
  ...(await orig<typeof import("../../../lib/http")>()), http,
}));

function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const spy = vi.spyOn(client, "invalidateQueries");
  const Wrap = ({ children }: { children: ReactNode }) =>
    <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  return { Wrap, spy };
}

describe("phc hooks", () => {
  beforeEach(() => vi.resetAllMocks());

  it("does not search patients until two characters are typed", () => {
    const { Wrap } = wrapper();
    renderHook(() => usePatientSearch("a"), { wrapper: Wrap });
    expect(http.get).not.toHaveBeenCalled();
  });

  it("does not request a report until one is asked for", () => {
    const { Wrap } = wrapper();
    renderHook(() => useReport(null), { wrapper: Wrap });
    expect(http.get).not.toHaveBeenCalled();
  });

  it("posts a claim and invalidates the module's queries", async () => {
    http.post.mockResolvedValue({ data: { id: 7 } });
    const { Wrap, spy } = wrapper();
    const { result } = renderHook(() => useSubmitClaim(), { wrapper: Wrap });
    await act(() => result.current.mutateAsync({ prescription_id: 17,
      expense_date: "2026-11-21", amount: "450.00", description: "" }));
    expect(http.post).toHaveBeenCalledWith("/phc/claims", { prescription_id: 17,
      expense_date: "2026-11-21", amount: "450.00", description: "" });
    await waitFor(() => expect(spy).toHaveBeenCalledWith({ queryKey: ["phc"] }));
  });

  it("sends a claim transition to its own claim's URL", async () => {
    http.post.mockResolvedValue({ data: {} });
    const { Wrap } = wrapper();
    const { result } = renderHook(() => useClaimTransition(), { wrapper: Wrap });
    await act(() => result.current.mutateAsync({ id: 9, event: "verify", note: "" }));
    expect(http.post).toHaveBeenCalledWith("/phc/claims/9/transition",
      { event: "verify", note: "" });
  });
});
