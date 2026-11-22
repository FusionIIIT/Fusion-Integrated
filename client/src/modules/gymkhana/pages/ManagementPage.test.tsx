import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { beforeEach, describe, expect, it, vi } from "vitest";

const useAuth = vi.hoisted(() => vi.fn());
const useClubs = vi.hoisted(() => vi.fn());
const useCreateClub = vi.hoisted(() => vi.fn());
const useConfirmClub = vi.hoisted(() => vi.fn());

vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));
vi.mock("../api/hooks", () => ({ useClubs, useCreateClub, useConfirmClub }));

import ManagementPage from "./ManagementPage";

describe("Gymkhana ManagementPage", () => {
  beforeEach(() => {
    useAuth.mockReturnValue({ can: (permission: string) => permission === "gymkhana.club.approve" });
    useClubs.mockReturnValue({ data: [], isPending: false });
    useCreateClub.mockReturnValue({ mutate: vi.fn(), isPending: false });
    useConfirmClub.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("shows empty state and hides unavailable create control", () => {
    render(
      <MantineProvider>
        <ManagementPage />
      </MantineProvider>,
    );
    expect(screen.getByText("No clubs")).toBeTruthy();
    expect(screen.queryByText("Create club")).toBeNull();
  });
});
