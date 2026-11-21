import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { FileListItem } from "../api/types";
import DraftsPage from "./DraftsPage";

const hooks = vi.hoisted(() => ({
  useDraftFiles: vi.fn(),
  useDiscardDraft: vi.fn(),
  useForwardFile: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleDraft: FileListItem = {
  id: 3,
  reference_number: "FTS-2026-0003",
  subject: "Draft Curriculum Proposal",
  status: "DRAFT",
  owner_user_id: 10,
  owner_username: "prof_smith",
  owner_role: "Professor",
  current_holder_user_id: 10,
  current_holder_username: "prof_smith",
  current_holder_role: "Professor",
  created_at: "2026-11-20T10:00:00Z",
  updated_at: "2026-11-20T11:00:00Z",
  archived_at: null,
};

describe("DraftsPage", () => {
  beforeEach(() => {
    hooks.useDraftFiles.mockReturnValue({
      data: [sampleDraft],
      isPending: false,
      error: null,
    });
    hooks.useDiscardDraft.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useForwardFile.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("renders draft files and action controls", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <DraftsPage />
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(screen.getByText("Draft Files")).toBeInTheDocument();
    expect(screen.getByText("FTS-2026-0003")).toBeInTheDocument();
    expect(screen.getByText("Draft Curriculum Proposal")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /circulate/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /discard/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /new file/i })).toBeInTheDocument();
  });

  it("renders empty state when no drafts exist", () => {
    hooks.useDraftFiles.mockReturnValue({
      data: [],
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <MemoryRouter>
          <DraftsPage />
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(screen.getByText("No drafts found")).toBeInTheDocument();
  });
});
