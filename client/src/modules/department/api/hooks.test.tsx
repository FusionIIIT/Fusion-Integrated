import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../pages/testUtils";
import { useDecideStock, useStockMovements, useStockRequests } from "./hooks";

vi.mock("../../../lib/http", async (orig) => (await import("../pages/testUtils")).httpMock(orig));

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidate = vi.spyOn(qc, "invalidateQueries");
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { Wrapper, invalidate };
}

describe("department hooks", () => {
  beforeEach(() => vi.clearAllMocks());

  it("passes a status filter only when one is given", async () => {
    api.get.mockResolvedValue({ data: { results: [] } });
    const { Wrapper } = wrapper();
    renderHook(() => useStockRequests("issued"), { wrapper: Wrapper });
    await waitFor(() => expect(api.get).toHaveBeenCalledWith("/department/stock-requests",
      { params: { status: "issued" } }));
  });

  it("does not fetch the movement log for a role that cannot see it", () => {
    const { Wrapper } = wrapper();
    renderHook(() => useStockMovements(false), { wrapper: Wrapper });
    expect(api.get).not.toHaveBeenCalled();
  });

  it("invalidates the module's queries after a write", async () => {
    api.post.mockResolvedValue({ data: { id: 1, status: "approved" } });
    const { Wrapper, invalidate } = wrapper();
    const { result } = renderHook(() => useDecideStock(), { wrapper: Wrapper });
    await act(() => result.current.mutateAsync({ id: 1, approve: true }));
    expect(api.post).toHaveBeenCalledWith("/department/stock-requests/1/decide", { approve: true });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["department"] });
  });
});
