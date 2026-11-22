import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProposalsListPage from "./ProposalsListPage";
import type { Proposal } from "../api/types";

const hooks = vi.hoisted(() => ({
  useProposals: vi.fn(),
  useCreateProposal: vi.fn(),
  useSubmitProposal: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

const fakeProposal: Proposal = {
  id: 1,
  user_id: 10,
  title: "Quantum Key Distribution",
  proposal_type: "sponsored_research",
  department: "CSE",
  funding_agency: "DST",
  proposed_budget: "500000.00",
  overhead_amount: "75000.00",
  submission_deadline: null,
  status: "draft",
  summary: "Quantum security testbed",
  created_at: "2026-11-20T00:00:00Z",
  updated_at: "2026-11-20T00:00:00Z",
};

describe("ProposalsListPage", () => {
  const submitMutateAsync = vi.fn().mockResolvedValue({});
  const createMutateAsync = vi.fn().mockResolvedValue({});

  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({
      can: (perm: string) => perm === "rspc.proposal.create",
    });
    hooks.useCreateProposal.mockReturnValue({
      mutateAsync: createMutateAsync,
      isPending: false,
    });
    hooks.useSubmitProposal.mockReturnValue({
      mutateAsync: submitMutateAsync,
      isPending: false,
    });
  });

  it("1. renders loading state while query is fetching", () => {
    hooks.useProposals.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(
      <MantineProvider>
        <ProposalsListPage />
      </MantineProvider>
    );

    expect(screen.getByText("Loading proposals...")).toBeInTheDocument();
  });

  it("2. renders empty state when no proposals exist", () => {
    hooks.useProposals.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    render(
      <MantineProvider>
        <ProposalsListPage />
      </MantineProvider>
    );

    expect(screen.getByText("No proposals found.")).toBeInTheDocument();
  });

  it("3. renders error state banner on API failure", () => {
    hooks.useProposals.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { response: { data: { error: { message: "Server down" } } } },
    });

    render(
      <MantineProvider>
        <ProposalsListPage />
      </MantineProvider>
    );

    expect(screen.getByText("Could not load this")).toBeInTheDocument();
    expect(screen.getByText("Server down")).toBeInTheDocument();
  });

  it("4. hides create control when permission is missing", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useProposals.mockReturnValue({
      data: [fakeProposal],
      isLoading: false,
      error: null,
    });

    render(
      <MantineProvider>
        <ProposalsListPage />
      </MantineProvider>
    );

    expect(screen.queryByRole("button", { name: /new proposal/i })).toBeNull();
    expect(screen.queryByRole("button", { name: "Submit" })).toBeNull();
  });

  it("5. triggers submit main action for draft proposal", async () => {
    hooks.useProposals.mockReturnValue({
      data: [fakeProposal],
      isLoading: false,
      error: null,
    });

    render(
      <MantineProvider>
        <ProposalsListPage />
      </MantineProvider>
    );

    const submitBtn = screen.getByRole("button", { name: "Submit" });
    expect(submitBtn).toBeInTheDocument();
    fireEvent.click(submitBtn);

    expect(submitMutateAsync).toHaveBeenCalledWith(1);
  });
});
