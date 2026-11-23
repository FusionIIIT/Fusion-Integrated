import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import type { FileAuditLog } from "../api/types";
import GovernancePage from "./GovernancePage";

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

const mockAuditLog: FileAuditLog = {
  id: 1,
  file_id: 105,
  actor_user_id: 3,
  actor_designation: "Dean Academic",
  action: "CREATED",
  payload: { note: "Initial submission" },
  ip_address: "127.0.0.1",
  created_at: "2026-11-22T14:30:00Z",
};

describe("GovernancePage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the loading state while the query is pending", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => {}));
    const { container } = renderWithProviders(<GovernancePage />);
    expect(container.querySelector(".mantine-Loader-root")).toBeInTheDocument();
  });

  it("shows the empty state when no audit records exist", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [] });
    renderWithProviders(<GovernancePage />);
    await waitFor(() => {
      expect(screen.getByText("No audit logs recorded yet.")).toBeInTheDocument();
    });
  });

  it("shows the error state when the API returns an error", async () => {
    vi.spyOn(http, "get").mockRejectedValue({
      response: { status: 500, data: { error: { message: "Permission denied or audit error" } } },
      message: "Audit service failure",
    });
    renderWithProviders(<GovernancePage />);
    await waitFor(() => {
      expect(screen.queryByText("No audit logs recorded yet.")).not.toBeInTheDocument();
      expect(screen.getByText(/error|failed|audit service failure/i)).toBeInTheDocument();
    });
  });

  it("renders audit logs with actions and actors", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [mockAuditLog] });
    renderWithProviders(<GovernancePage />);
    await waitFor(() => {
      expect(screen.getByText("CREATED")).toBeInTheDocument();
      expect(screen.getByText(/Dean Academic/i)).toBeInTheDocument();
      expect(screen.getByText("127.0.0.1")).toBeInTheDocument();
    });
  });
});
