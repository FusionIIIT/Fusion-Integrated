import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { FileListItem } from "../api/types";
import InboxPage from "./InboxPage";

const hooks = vi.hoisted(() => ({
  useInboxFiles: vi.fn(),
  useArchiveFile: vi.fn(),
  useFileDetail: vi.fn(),
  useFileHistory: vi.fn(),
  useForwardFile: vi.fn(),
  useReturnFile: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

const sampleFile: FileListItem = {
  id: 1,
  reference_number: "FTS-2026-0001",
  subject: "Lab Budget Approval",
  status: "CIRCULATED",
  owner_user_id: 10,
  owner_username: "prof_smith",
  owner_role: "Professor",
  current_holder_user_id: 20,
  current_holder_username: "registrar_office",
  current_holder_role: "Registrar",
  created_at: "2026-11-20T10:00:00Z",
  updated_at: "2026-11-20T11:00:00Z",
  archived_at: null,
};

describe("InboxPage", () => {
  const mockArchiveMutate = vi.fn();

  beforeEach(() => {
    mockArchiveMutate.mockReset();
    useAuth.mockReturnValue({
      session: { user: { id: 20, username: "registrar_office" } },
      can: vi.fn().mockReturnValue(true),
    });
    hooks.useInboxFiles.mockReturnValue({
      data: [sampleFile],
      isPending: false,
      error: null,
    });
    hooks.useArchiveFile.mockReturnValue({ mutate: mockArchiveMutate, isPending: false });
    hooks.useFileDetail.mockReturnValue({ data: null, isPending: false, error: null });
    hooks.useFileHistory.mockReturnValue({ data: [], isPending: false, error: null });
    hooks.useForwardFile.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useReturnFile.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("renders inbox header and file row with actions", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <InboxPage />
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(screen.getByText("File Inbox")).toBeInTheDocument();
    expect(screen.getByText("FTS-2026-0001")).toBeInTheDocument();
    expect(screen.getByText("Lab Budget Approval")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /forward/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /return/i })).toBeInTheDocument();
    // Non-owner should not see archive button
    expect(screen.queryByRole("button", { name: /archive/i })).not.toBeInTheDocument();
  });

  it("shows archive button when current user is file owner and calls mutate on confirmation", () => {
    useAuth.mockReturnValue({
      session: { user: { id: 10, username: "prof_smith" } },
      can: vi.fn().mockReturnValue(true),
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(
      <MantineProvider>
        <MemoryRouter>
          <InboxPage />
        </MemoryRouter>
      </MantineProvider>,
    );

    const archiveBtn = screen.getByRole("button", { name: /archive/i });
    expect(archiveBtn).toBeInTheDocument();
    fireEvent.click(archiveBtn);
    expect(mockArchiveMutate).toHaveBeenCalledWith(1);
  });

  it("renders error state when hook fails", () => {
    hooks.useInboxFiles.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Network error loading inbox"),
    });

    render(
      <MantineProvider>
        <MemoryRouter>
          <InboxPage />
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("renders empty state when no files exist", () => {
    hooks.useInboxFiles.mockReturnValue({
      data: [],
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <MemoryRouter>
          <InboxPage />
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(screen.getByText("Inbox is empty")).toBeInTheDocument();
  });
});
