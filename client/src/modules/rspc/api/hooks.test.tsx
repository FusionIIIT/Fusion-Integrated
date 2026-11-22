import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import {
  useCreateProposal,
  useProjects,
  useProposals,
  useSubmitProposal,
} from "./hooks";
import type { Project, Proposal } from "./types";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("RSPC TanStack Query hooks", () => {
  it("useProposals fetches proposals via http.get", async () => {
    const fakeProposals: Proposal[] = [
      {
        id: 1,
        user_id: 10,
        title: "Test Proposal",
        proposal_type: "sponsored_research",
        department: "CSE",
        funding_agency: "DST",
        proposed_budget: "100000.00",
        overhead_amount: "15000.00",
        submission_deadline: null,
        status: "draft",
        summary: "Summary",
        created_at: "2026-11-20T00:00:00Z",
        updated_at: "2026-11-20T00:00:00Z",
      },
    ];

    vi.spyOn(http, "get").mockResolvedValueOnce({ data: fakeProposals });

    const { result } = renderHook(() => useProposals(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(fakeProposals);
    expect(http.get).toHaveBeenCalledWith("/rspc/proposals/", {
      params: undefined,
    });
  });

  it("useProjects fetches projects via http.get", async () => {
    const fakeProjects: Project[] = [
      {
        id: 1,
        project_code: "P-101",
        project_type: "sponsored",
        title: "Test Project",
        user_id: 10,
        department: "CSE",
        funding_agency: "DST",
        sanction_order_no: "SO-1",
        sanction_date: "2026-11-20",
        start_date: "2026-11-20",
        end_date: "2027-11-20",
        sanctioned_amount: "500000.00",
        status: "active",
        created_at: "2026-11-20T00:00:00Z",
        updated_at: "2026-11-20T00:00:00Z",
      },
    ];

    vi.spyOn(http, "get").mockResolvedValueOnce({ data: fakeProjects });

    const { result } = renderHook(() => useProjects(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(fakeProjects);
    expect(http.get).toHaveBeenCalledWith("/rspc/projects/", {
      params: undefined,
    });
  });

  it("useCreateProposal calls http.post and returns new proposal", async () => {
    const newProposal = { id: 2, title: "New", status: "draft" };
    vi.spyOn(http, "post").mockResolvedValueOnce({ data: newProposal });

    const { result } = renderHook(() => useCreateProposal(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ title: "New", proposal_type: "sponsored_research" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/rspc/proposals/", {
      title: "New",
      proposal_type: "sponsored_research",
    });
  });

  it("useSubmitProposal calls submit action endpoint", async () => {
    vi.spyOn(http, "post").mockResolvedValueOnce({ data: { id: 1, status: "submitted_hod" } });

    const { result } = renderHook(() => useSubmitProposal(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(1);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/rspc/proposals/1/submit/");
  });
});
