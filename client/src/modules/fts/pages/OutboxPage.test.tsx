import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { FileListItem } from "../api/types";
import OutboxPage from "./OutboxPage";

const hooks = vi.hoisted(() => ({
  useOutboxFiles: vi.fn(),
  useFileDetail: vi.fn(),
  useFileHistory: vi.fn(),
  useArchiveFile: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

const sampleFile: FileListItem = {
  id: 2,
  reference_number: "FTS-2026-0002",
  subject: "Conference Travel Claim",
  status: "CIRCULATED",
  owner_user_id: 10,
  owner_username: "prof_smith",
  owner_role: "Professor",
  current_holder_user_id: 30,
  current_holder_username: "dean_acad",
  current_holder_role: "Dean Academic",
  created_at: "2026-11-20T10:00:00Z",
  updated_at: "2026-11-20T11:00:00Z",
  archived_at: null,
};

describe("OutboxPage", () => {
  beforeEach(() => {
    useAuth.mockReturnValue({
      session: { user: { id: 10, username: "prof_smith" } },
      can: vi.fn().mockReturnValue(true),
    });
    hooks.useOutboxFiles.mockReturnValue({
      data: [sampleFile],
      isPending: false,
      error: null,
    });
    hooks.useFileDetail.mockReturnValue({ data: null, isPending: false, error: null });
    hooks.useFileHistory.mockReturnValue({ data: [], isPending: false, error: null });
    hooks.useArchiveFile.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("renders outbox header and tracking row", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <OutboxPage />
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(screen.getByText("File Outbox")).toBeInTheDocument();
    expect(screen.getByText("FTS-2026-0002")).toBeInTheDocument();
    expect(screen.getByText("Conference Travel Claim")).toBeInTheDocument();
    expect(screen.getByText(/dean_acad/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /view history/i })).toBeInTheDocument();
  });

  it("renders empty state when outbox is empty", () => {
    hooks.useOutboxFiles.mockReturnValue({
      data: [],
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <MemoryRouter>
          <OutboxPage />
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(screen.getByText("Outbox is empty")).toBeInTheDocument();
  });
});
