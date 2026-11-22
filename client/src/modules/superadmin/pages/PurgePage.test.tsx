import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PurgeRequest } from "../api/types";
import PurgePage from "./PurgePage";

const hooks = vi.hoisted(() => ({
  usePurgeRequests: vi.fn(),
  useCreatePurgeRequest: vi.fn(),
  useDecidePurgeRequest: vi.fn(),
  useExecutePurge: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const pendingPurge: PurgeRequest = {
  id: 10,
  archive: 1,
  archive_title: "Placement 2021 Data",
  dataset_category: "placement",
  requested_by: 1,
  requested_at: "2026-11-01T10:00:00Z",
  request_reason: "Mandatory 5-year retention expired",
  status: "pending_it_head",
  it_head_id: null,
  it_head_decision_at: null,
  it_head_comments: "",
  purged_at: null,
  execution_summary: {},
  created_at: "2026-11-01T10:00:00Z",
  updated_at: "2026-11-01T10:00:00Z",
};

const approvedPurge: PurgeRequest = {
  ...pendingPurge,
  id: 11,
  status: "approved",
  it_head_id: 2,
};

const completedPurge: PurgeRequest = {
  ...pendingPurge,
  id: 12,
  status: "purged",
};

describe("PurgePage", () => {
  const mockCreatePurge = { mutate: vi.fn(), isPending: false };
  const mockDecide = { mutate: vi.fn(), isPending: false };
  const mockExecute = { mutate: vi.fn(), isPending: false };

  beforeEach(() => {
    vi.restoreAllMocks();
    mockCreatePurge.mutate.mockReset();
    mockDecide.mutate.mockReset();
    mockExecute.mutate.mockReset();
    hooks.useCreatePurgeRequest.mockReturnValue(mockCreatePurge);
    hooks.useDecidePurgeRequest.mockReturnValue(mockDecide);
    hooks.useExecutePurge.mockReturnValue(mockExecute);
  });

  it("renders loader during loading state", () => {
    hooks.usePurgeRequests.mockReturnValue({
      data: null,
      isPending: true,
      error: null,
    });

    const { container } = render(
      <MantineProvider>
        <PurgePage />
      </MantineProvider>,
    );
    expect(container.querySelector(".mantine-Loader-root")).toBeInTheDocument();
  });

  it("renders empty state placeholder when no purge requests exist", () => {
    hooks.usePurgeRequests.mockReturnValue({
      data: { count: 0, next: null, previous: null, results: [] },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <PurgePage />
      </MantineProvider>,
    );
    expect(screen.getByText("No purge requests")).toBeInTheDocument();
  });

  it("renders error state on 500 error", () => {
    hooks.usePurgeRequests.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Internal Server Error 500"),
    });

    render(
      <MantineProvider>
        <PurgePage />
      </MantineProvider>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("hides approve/execute controls for finalized purged requests", () => {
    hooks.usePurgeRequests.mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [completedPurge] },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <PurgePage />
      </MantineProvider>,
    );
    expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Reject" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Execute Purge" })).toBeNull();
  });

  it("allows IT Head decision on pending requests", async () => {
    hooks.usePurgeRequests.mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [pendingPurge] },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <PurgePage />
      </MantineProvider>,
    );

    const approveBtn = screen.getByRole("button", { name: "Approve" });
    expect(approveBtn).toBeInTheDocument();
    fireEvent.click(approveBtn);

    const dialog = await screen.findByRole("dialog");
    const commentsInput = within(dialog).getByLabelText("Comments");
    fireEvent.change(commentsInput, { target: { value: "Approved by IT Head." } });

    fireEvent.click(within(dialog).getByRole("button", { name: "Approve" }));

    expect(mockDecide.mutate).toHaveBeenCalledWith(
      { id: 10, approve: true, comments: "Approved by IT Head." },
      expect.any(Object),
    );
  });

  it("allows executing an approved purge request", async () => {
    hooks.usePurgeRequests.mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [approvedPurge] },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <PurgePage />
      </MantineProvider>,
    );

    const execBtn = screen.getByRole("button", { name: "Execute Purge" });
    expect(execBtn).toBeInTheDocument();
    fireEvent.click(execBtn);

    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirm Permanent Purge" }));

    expect(mockExecute.mutate).toHaveBeenCalledWith(11, expect.any(Object));
  });

  it("allows initiating a new purge request", async () => {
    hooks.usePurgeRequests.mockReturnValue({
      data: { count: 0, next: null, previous: null, results: [] },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <PurgePage />
      </MantineProvider>,
    );

    const initBtn = screen.getByRole("button", { name: "Initiate Purge" });
    fireEvent.click(initBtn);

    const dialog = await screen.findByRole("dialog");
    const archiveInput = within(dialog).getByLabelText(/^Dataset Archive ID/i);
    const reasonInput = within(dialog).getByLabelText(/^Request reason/i);

    fireEvent.change(archiveInput, { target: { value: "42" } });
    fireEvent.change(reasonInput, { target: { value: "Mandatory compliance expiration." } });

    fireEvent.click(within(dialog).getByRole("button", { name: "Create Purge Request" }));

    expect(mockCreatePurge.mutate).toHaveBeenCalledWith(
      { archive_id: 42, request_reason: "Mandatory compliance expiration." },
      expect.any(Object),
    );
  });
});
