import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import {
  useApplyLeave,
  useCancelLeave,
  useLeaveBalances,
  useLeaveCatalog,
  useMyLeaveRequests,
  useRespondSubstitute,
  useReviewDecision,
  useReviewTasks,
  useSubstituteTasks,
  useWithdrawLeave,
} from "./hooks";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
});

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("ELM API hooks", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.restoreAllMocks();
  });

  it.each([
    [useLeaveCatalog, "/elm/catalog", { entitlements: { CL: "8" } }],
    [useLeaveBalances, "/elm/balances", []],
    [useMyLeaveRequests, "/elm/requests", []],
    [useSubstituteTasks, "/elm/tasks/substitute", []],
    [useReviewTasks, "/elm/tasks/review", []],
  ])("queries %s from the matching endpoint", async (hook, endpoint, data) => {
    const get = vi.spyOn(http, "get").mockResolvedValue({ data });
    const { result } = renderHook(() => hook(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(get).toHaveBeenCalledWith(endpoint);
  });

  it("applies leave and invalidates request and balance data", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 7 } });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useApplyLeave(), { wrapper });
    const payload = { category: "CL", start_date: "2026-11-02", end_date: "2026-11-02", purpose: "Test" };

    result.current.mutate(payload);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(post).toHaveBeenCalledWith("/elm/requests", payload);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["elm", "requests"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["elm", "balances"] });
  });

  it("withdraws a request and invalidates request history", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 9 } });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useWithdrawLeave(), { wrapper });
    result.current.mutate(9);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(post).toHaveBeenCalledWith("/elm/requests/9/withdraw");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["elm", "requests"] });
  });

  it("cancels a request and refreshes both history and balances", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 10 } });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useCancelLeave(), { wrapper });
    result.current.mutate(10);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(post).toHaveBeenCalledWith("/elm/requests/10/cancel");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["elm", "requests"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["elm", "balances"] });
  });

  it.each(["accept", "decline"] as const)("responds to substitute request with %s", async (action) => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { status: action === "accept" ? "accepted" : "declined" } });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useRespondSubstitute(), { wrapper });
    result.current.mutate({ requestId: 11, action, remarks: "Noted" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(post).toHaveBeenCalledWith("/elm/tasks/substitute/11/respond", { action, remarks: "Noted" });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["elm", "tasks", "substitute"] });
  });

  it.each(["approve", "reject", "recommend"] as const)("submits review decision %s", async (action) => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { status: "updated" } });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useReviewDecision(), { wrapper });
    result.current.mutate({ requestId: 12, action, reason: "Reviewed" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(post).toHaveBeenCalledWith("/elm/tasks/review/12/decision", { action, reason: "Reviewed" });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["elm", "tasks", "review"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["elm", "balances"] });
  });
});
