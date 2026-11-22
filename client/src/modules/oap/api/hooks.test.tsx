import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { useLeaves, useSubmitLeave } from "./hooks";
import type { StudentLeaveRequest } from "./types";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("OAP hooks", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("useLeaves fetches list of student leave applications", async () => {
    const mockLeaves: StudentLeaveRequest[] = [
      {
        id: 1,
        student_id: "24BCS205",
        student_name: "Rahul Kumar",
        leave_type: "CASUAL",
        start_date: "2026-12-01",
        end_date: "2026-12-05",
        duration_days: 5,
        reason: "Test",
        status: "PENDING",
        document_url: "",
        created_at: "2026-11-20T10:00:00Z",
        updated_at: "2026-11-20T10:00:00Z",
      },
    ];

    vi.spyOn(http, "get").mockResolvedValue({
      data: { results: mockLeaves, next: null, previous: null },
    });

    const { result } = renderHook(() => useLeaves(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.results).toHaveLength(1);
    expect(result.current.data?.results?.[0]?.student_id).toBe("24BCS205");
    expect(http.get).toHaveBeenCalledWith("/oap/leave/");
  });

  it("useSubmitLeave posts a new leave application", async () => {
    const newLeave = {
      student_id: "24BCS205",
      student_name: "Rahul Kumar",
      leave_type: "CASUAL",
      start_date: "2026-12-01",
      end_date: "2026-12-05",
      reason: "Attending hackathon",
    };

    vi.spyOn(http, "post").mockResolvedValue({
      data: { id: 10, ...newLeave, duration_days: 5, status: "PENDING" },
    });

    const { result } = renderHook(() => useSubmitLeave(), { wrapper });
    result.current.mutate(newLeave);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/oap/leave/", newLeave);
  });
});
