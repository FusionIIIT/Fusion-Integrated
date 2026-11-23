import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import type { TrackedFileSummary } from "../api/types";
import OutboxPage from "./OutboxPage";

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
  id: 102,
  file_number: "FTS-2026-0002",
  subject: "Conference Travel Grant",
  status: "circulating",
  created_by_user_id: 2,
  creator_designation: "Assistant Professor",
  current_holder_user_id: 4,
  current_holder_designation: "Dean Academic",
  is_archived: false,
  created_at: "2026-11-21T09:00:00Z",
  updated_at: "2026-11-21T11:00:00Z",
  archived_at: null,
};

describe("OutboxPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the loading state while the query is pending", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => {}));
    const { container } = renderWithProviders(<OutboxPage />);
    expect(container.querySelector(".mantine-Loader-root")).toBeInTheDocument();
  });

  it("shows the empty state when outbox is empty", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [] });
    renderWithProviders(<OutboxPage />);
    await waitFor(() => {
      expect(screen.getByText("No files in outbox.")).toBeInTheDocument();
    });
  });

  it("shows the error state when the API returns an error", async () => {
    vi.spyOn(http, "get").mockRejectedValue({
      response: { status: 500, data: { error: { message: "Internal server error" } } },
      message: "Server unreachable",
    });
    renderWithProviders(<OutboxPage />);
    await waitFor(() => {
      expect(screen.queryByText("No files in outbox.")).not.toBeInTheDocument();
      expect(screen.getByText(/error|failed|server unreachable/i)).toBeInTheDocument();
    });
  });

  it("renders file details when outbox records exist", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [mockFile] });
    renderWithProviders(<OutboxPage />);
    await waitFor(() => {
      expect(screen.getByText("FTS-2026-0002")).toBeInTheDocument();
      expect(screen.getByText("Conference Travel Grant")).toBeInTheDocument();
      expect(screen.getByText("Dean Academic")).toBeInTheDocument();
    });
  });
});
