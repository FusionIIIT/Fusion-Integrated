import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import FinanceLedgerPage from "./FinanceLedgerPage";
import type { Project, ProjectFundTransaction } from "../api/types";

const hooks = vi.hoisted(() => ({
  useProjects: vi.fn(),
  useLedger: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const fakeProject: Project = {
  id: 1,
  project_code: "P-101",
  project_type: "sponsored",
  title: "AI Grant",
  user_id: 10,
  department: "CSE",
  funding_agency: "DST",
  sanction_order_no: "SO-1",
  sanction_date: "2026-01-01",
  start_date: "2026-01-01",
  end_date: "2027-01-01",
  sanctioned_amount: "500000.00",
  status: "active",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const fakeTx: ProjectFundTransaction = {
  id: 42,
  project_id: 1,
  budget_head_id: 10,
  head_type: "Equipment",
  transaction_type: "disbursement",
  amount: "50000.00",
  reference_no: "TX-9988",
  description: "GPU server purchase",
  created_by_user_id: 10,
  created_at: "2026-02-01T10:00:00Z",
};

describe("FinanceLedgerPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. renders loading state while query is fetching", () => {
    hooks.useProjects.mockReturnValue({
      data: [fakeProject],
      isLoading: false,
      error: null,
    });
    hooks.useLedger.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(
      <MantineProvider>
        <FinanceLedgerPage />
      </MantineProvider>
    );

    expect(screen.getByText("Loading ledger transactions...")).toBeInTheDocument();
  });

  it("2. renders empty state when no transactions exist", () => {
    hooks.useProjects.mockReturnValue({
      data: [fakeProject],
      isLoading: false,
      error: null,
    });
    hooks.useLedger.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    render(
      <MantineProvider>
        <FinanceLedgerPage />
      </MantineProvider>
    );

    expect(
      screen.getByText("No transactions recorded for this project.")
    ).toBeInTheDocument();
  });

  it("3. renders error banner on query error", () => {
    hooks.useProjects.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { response: { data: { error: { message: "Ledger access forbidden" } } } },
    });
    hooks.useLedger.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });

    render(
      <MantineProvider>
        <FinanceLedgerPage />
      </MantineProvider>
    );

    expect(screen.getByText("Could not load this")).toBeInTheDocument();
    expect(screen.getByText("Ledger access forbidden")).toBeInTheDocument();
  });

  it("4. renders transaction rows when data is loaded", () => {
    hooks.useProjects.mockReturnValue({
      data: [fakeProject],
      isLoading: false,
      error: null,
    });
    hooks.useLedger.mockReturnValue({
      data: [fakeTx],
      isLoading: false,
      error: null,
    });

    render(
      <MantineProvider>
        <FinanceLedgerPage />
      </MantineProvider>
    );

    expect(screen.getByText("#42")).toBeInTheDocument();
    expect(screen.getByText("Equipment")).toBeInTheDocument();
    expect(screen.getByText("TX-9988")).toBeInTheDocument();
    expect(screen.getByText("GPU server purchase")).toBeInTheDocument();
  });
});
