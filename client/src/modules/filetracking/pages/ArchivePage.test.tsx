import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import type { TrackedFileSummary } from "../api/types";
import ArchivePage from "./ArchivePage";

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

const mockArchivedFile: TrackedFileSummary = {
  id: 104,
  file_number: "FTS-2026-0004",
  subject: "Annual Sports Budget 2025",
  status: "archived",
  created_by_user_id: 2,
  creator_designation: "Assistant Professor",
  current_holder_user_id: 2,
  current_holder_designation: "Assistant Professor",
  is_archived: true,
  created_at: "2026-01-10T10:00:00Z",
  updated_at: "2026-02-15T15:00:00Z",
  archived_at: "2026-02-15T15:00:00Z",
};

describe("ArchivePage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the loading state while the query is pending", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => {}));
    const { container } = renderWithProviders(<ArchivePage />);
    expect(container.querySelector(".mantine-Loader-root")).toBeInTheDocument();
  });

  it("shows the empty state when no files are archived", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [] });
    renderWithProviders(<ArchivePage />);
    await waitFor(() => {
      expect(screen.getByText("No archived files found.")).toBeInTheDocument();
    });
  });

  it("shows the error state when the API returns an error", async () => {
    vi.spyOn(http, "get").mockRejectedValue({
      response: { status: 500, data: { error: { message: "Failed to load archive" } } },
      message: "Failed to load archive",
    });
    renderWithProviders(<ArchivePage />);
    await waitFor(() => {
      expect(screen.queryByText("No archived files found.")).not.toBeInTheDocument();
      expect(screen.getByText(/error|failed/i)).toBeInTheDocument();
    });
  });

  it("renders archived records with file numbers and statuses", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [mockArchivedFile] });
    renderWithProviders(<ArchivePage />);
    await waitFor(() => {
      expect(screen.getByText("FTS-2026-0004")).toBeInTheDocument();
      expect(screen.getByText("Annual Sports Budget 2025")).toBeInTheDocument();
      expect(screen.getByText("archived")).toBeInTheDocument();
    });
  });
});
