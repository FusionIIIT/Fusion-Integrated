/** What the mutations actually send, and what they invalidate afterwards. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { useApply, useRoute, useSubmitResumption, useWithdraw } from "./hooks";

let qc: QueryClient;

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
});

describe("leave mutations", () => {
  it("posts an application to the collection, not to a person", async () => {
    // The applicant comes from the credential, so the body never names one.
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 1 } });

    const { result } = renderHook(() => useApply(), { wrapper });
    result.current.mutate({
      category: "CL", starts_on: "2026-03-02", ends_on: "2026-03-03",
      reason: "Personal work",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(post).toHaveBeenCalledWith("/leave/requests", {
      category: "CL", starts_on: "2026-03-02", ends_on: "2026-03-03",
      reason: "Personal work",
    });
  });

  it("invalidates the whole module after a decision", async () => {
    vi.spyOn(http, "post").mockResolvedValue({ data: { id: 7 } });
    const invalidate = vi.spyOn(qc, "invalidateQueries");

    const { result } = renderHook(() => useRoute(), { wrapper });
    result.current.mutate({ id: 7, remark: "Forwarded" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["leave"] });
  });

  it("sends the resumption date, which is what restores unused days", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 3 } });

    const { result } = renderHook(() => useSubmitResumption(), { wrapper });
    result.current.mutate({ id: 3, resumed_on: "2026-03-05", remark: "" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(post).toHaveBeenCalledWith(
      "/leave/requests/3/resumption",
      { id: 3, resumed_on: "2026-03-05", remark: "" });
  });

  it("withdraws by id, with the remark optional", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 4 } });

    const { result } = renderHook(() => useWithdraw(), { wrapper });
    result.current.mutate({ id: 4 });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(post).toHaveBeenCalledWith(
      "/leave/requests/4/withdraw", { remark: undefined });
  });
});
