/** The write paths: the URL, the payload, and what a refusal looks like. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { errorMessage, http } from "../../../lib/http";
import { useMyApplications, useSubmitLeave, useTransition } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useMyApplications", () => {
  it("reads the module's own list endpoint", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: { results: [], next: null, previous: null },
    });

    const { result } = renderHook(() => useMyApplications({ status: "pending" }),
                                  { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/elm/applications",
                                          { params: { status: "pending" } });
  });
});

describe("useSubmitLeave", () => {
  it("posts the request to the submit endpoint", async () => {
    vi.spyOn(http, "post").mockResolvedValue({
      data: { id: 7, status: "pending" },
    });

    const { result } = renderHook(() => useSubmitLeave(), { wrapper });
    result.current.mutate({
      leave_type_id: 1, start_date: "2026-04-20", end_date: "2026-04-21",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/elm/applications/submit", {
      leave_type_id: 1, start_date: "2026-04-20", end_date: "2026-04-21",
    });
  });

  it("leaves the server's refusal readable for the toast", async () => {
    vi.spyOn(http, "post").mockRejectedValue({
      response: {
        status: 409,
        data: { error: { code: "overlapping_leave", message: "Overlaps." } },
      },
    });

    const { result } = renderHook(() => useSubmitLeave(), { wrapper });
    result.current.mutate({
      leave_type_id: 1, start_date: "2026-04-20", end_date: "2026-04-20",
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(errorMessage(result.current.error)).toBe("Overlaps.");
  });
});

describe("useTransition", () => {
  it("posts the decision to the application's transition endpoint", async () => {
    vi.spyOn(http, "post").mockResolvedValue({
      data: { id: 7, status: "approved" },
    });

    const { result } = renderHook(() => useTransition(), { wrapper });
    result.current.mutate({ id: 7, to_status: "approved", note: "Approved" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/elm/applications/7/transition", {
      to_status: "approved", note: "Approved",
    });
  });

  it("sends an empty note rather than nothing, so the field is always present",
    async () => {
      vi.spyOn(http, "post").mockResolvedValue({
        data: { id: 7, status: "withdrawn" },
      });

      const { result } = renderHook(() => useTransition(), { wrapper });
      result.current.mutate({ id: 7, to_status: "withdrawn" });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.post).toHaveBeenCalledWith("/elm/applications/7/transition", {
        to_status: "withdrawn", note: "",
      });
    });
});
