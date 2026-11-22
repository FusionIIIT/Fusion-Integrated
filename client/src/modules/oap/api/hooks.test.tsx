import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { unwrap, useLeaves, useLeaveDecision } from "./hooks";
import type { Leave } from "./types";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const row: Leave = {
  id: 7, status: "submitted", reason: "Family", from_date: "2026-12-01",
  to_date: "2026-12-03", supporting_document_link: "", decided_at: null,
  created_at: "2026-11-23T10:00:00Z",
};

describe("unwrap", () => {
  it("takes the rows from a cursor page", () => {
    expect(unwrap({ results: [row], next: null, previous: null })).toEqual([row]);
  });

  it("passes a plain array through", () => {
    expect(unwrap([row])).toEqual([row]);
  });
});

describe("OAP data hooks", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("reads leave applications from the module path", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [row], next: null, previous: null } });
    const { result } = renderHook(() => useLeaves(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/oap/leave-applications");
    expect(result.current.data).toEqual([row]);
  });

  it("posts a decision to the decision endpoint", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { ...row, status: "approved" } });
    const { result } = renderHook(() => useLeaveDecision(), { wrapper });
    result.current.mutate({ id: 7, outcome: "approve" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(post).toHaveBeenCalledWith("/oap/leave-applications/7/decision", { outcome: "approve" });
  });
});
