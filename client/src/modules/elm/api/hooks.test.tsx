/** The write hooks post to the right endpoint and refresh the module's data. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as download from "../../../lib/download";
import { http } from "../../../lib/http";
import { useDecide, useEmployeeSearch, usePrint, useWithdraw } from "./hooks";

function setup() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const invalidate = vi.spyOn(qc, "invalidateQueries");
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { wrapper, invalidate };
}

afterEach(() => vi.restoreAllMocks());

describe("elm hooks", () => {
  it("records a decision against the queue endpoint and refreshes", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 7 } });
    const { wrapper, invalidate } = setup();
    const { result } = renderHook(() => useDecide(), { wrapper });
    result.current.mutate({ id: 7, event: "reject", note: "short staffed" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(post).toHaveBeenCalledWith("/elm/queue/7/decide",
      { event: "reject", note: "short staffed" });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["elm"] });
  });

  it("withdraws with a reason only", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: {} });
    const { wrapper } = setup();
    const { result } = renderHook(() => useWithdraw(), { wrapper });
    result.current.mutate({ id: 3, reason: "plans changed" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(post).toHaveBeenCalledWith("/elm/requests/3/withdraw", { reason: "plans changed" });
  });

  it("does not search the directory for a single letter", () => {
    const get = vi.spyOn(http, "get");
    const { wrapper } = setup();
    renderHook(() => useEmployeeSearch("a"), { wrapper });
    expect(get).not.toHaveBeenCalled();
  });

  it("saves the printable application instead of navigating to it", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: new Blob(["x"]), headers: {} });
    const save = vi.spyOn(download, "saveBlob").mockImplementation(() => undefined);
    const { wrapper } = setup();
    const { result } = renderHook(() => usePrint(), { wrapper });
    result.current.mutate(12);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(save).toHaveBeenCalledWith(expect.any(Blob), "leave-12.txt");
  });
});
