import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import type { TrackedFileSummary } from "../api/types";
import InboxPage from "./InboxPage";

function renderWithProviders(ui: ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MantineProvider>
      <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
    </MantineProvider>
  );
}

const mockFile: TrackedFileSummary = {
  id: 101,
  file_number: "FTS-2026-0001",
  subject: "Lab Equipment Requisition",
  status: "circulating",
  created_by_user_id: 2,
  creator_designation: "Assistant Professor",
  current_holder_user_id: 3,
  current_holder_designation: "Head of Department",
  is_archived: false,
  created_at: "2026-11-20T10:00:00Z",
  updated_at: "2026-11-20T12:00:00Z",
  archived_at: null,
};

describe("InboxPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the loading state while the query is pending", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => {}));
    const { container } = renderWithProviders(<InboxPage />);
    expect(container.querySelector(".mantine-Loader-root")).toBeInTheDocument();
  });

  it("shows the empty state when the inbox has zero files", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [] });
    renderWithProviders(<InboxPage />);
    await waitFor(() => {
      expect(screen.getByText("Your inbox is empty.")).toBeInTheDocument();
    });
  });

  it("shows the error state when the API call fails", async () => {
    vi.spyOn(http, "get").mockRejectedValue({
      response: { status: 500, data: { error: { message: "Server down" } } },
      message: "Network error",
    });
    renderWithProviders(<InboxPage />);
    await waitFor(() => {
      expect(screen.queryByText("Your inbox is empty.")).not.toBeInTheDocument();
      expect(screen.getByText("Could not load this")).toBeInTheDocument();
      expect(screen.getByText("Server down")).toBeInTheDocument();
    });
  });

  it("renders files and columns when files exist", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [mockFile] });
    renderWithProviders(<InboxPage />);
    await waitFor(() => {
      expect(screen.getByText("FTS-2026-0001")).toBeInTheDocument();
      expect(screen.getByText("Lab Equipment Requisition")).toBeInTheDocument();
      expect(screen.getByText("circulating")).toBeInTheDocument();
    });
  });
});
