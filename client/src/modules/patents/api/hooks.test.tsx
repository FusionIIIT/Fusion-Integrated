import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import {
  useApplications,
  useAttorneyPanel,
  useCreateApplication,
  usePriorArtSearch,
  useReports,
} from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("patents query and mutation hooks", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches application list successfully", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 1,
            application_number: "PMS-2026-001",
            title: "Autonomous Drone",
            status: "DRAFT",
            domain_category: "Computer Science",
            jurisdiction: "IN",
          },
        ],
        next: null,
        previous: null,
      },
    });

    const { result } = renderHook(() => useApplications(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.results).toHaveLength(1);
    expect(result.current.data?.results[0]?.title).toBe("Autonomous Drone");
  });

  it("posts new application submission", async () => {
    vi.spyOn(http, "post").mockResolvedValueOnce({
      data: {
        id: 2,
        title: "Novel Solar Cell",
        status: "SUBMITTED",
        domain_category: "Material Sciences",
        jurisdiction: "IN",
      },
    });

    const { result } = renderHook(() => useCreateApplication(), { wrapper });
    result.current.mutate({
      title: "Novel Solar Cell",
      domain_category: "Material Sciences",
      jurisdiction: "IN",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe(2);
    expect(result.current.data?.status).toBe("SUBMITTED");
  });

  it("executes prior art search", async () => {
    vi.spyOn(http, "post").mockResolvedValueOnce({
      data: {
        query: "quantum computing",
        results: ["US9876543 - Quantum Gate System"],
      },
    });

    const { result } = renderHook(() => usePriorArtSearch(), { wrapper });
    result.current.mutate("quantum computing");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.results).toContain("US9876543 - Quantum Gate System");
  });

  it("fetches reports data", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        total_applications: 15,
        filed_count: 8,
        granted_count: 3,
      },
    });

    const { result } = renderHook(() => useReports(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.total_applications).toBe(15);
    expect(result.current.data?.filed_count).toBe(8);
    expect(result.current.data?.granted_count).toBe(3);
  });

  it("fetches attorney panel list", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 1,
            user_id: 42,
            firm_name: "Apex IP Law",
            active_workload: 2,
            is_approved_panel: true,
          },
        ],
        next: null,
        previous: null,
      },
    });

    const { result } = renderHook(() => useAttorneyPanel(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.results[0]?.firm_name).toBe("Apex IP Law");
  });
});
