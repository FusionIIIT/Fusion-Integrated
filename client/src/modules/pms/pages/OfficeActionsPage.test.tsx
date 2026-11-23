import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { application } from "./pageTestFixtures";
import OfficeActionsPage from "./OfficeActionsPage";

const hooks = vi.hoisted(() => ({ usePmsApplications: vi.fn(), usePmsApplication: vi.fn(), useOfficeActions: vi.fn() }));
const auth = vi.hoisted(() => ({ can: vi.fn() }));
vi.mock("../api/hooks", () => hooks);
vi.mock("../../../auth/AuthProvider", () => ({ useAuth: () => auth }));

describe("OfficeActionsPage (UC-PMS-014, UC-PMS-015)", () => {
  beforeEach(() => {
    auth.can.mockReturnValue(false);
    hooks.usePmsApplications.mockReturnValue({ data: [application], isPending: false, error: null });
    hooks.usePmsApplication.mockReturnValue({ data: application, isPending: false, error: null });
    hooks.useOfficeActions.mockReturnValue({ data: [], isPending: false, error: null });
  });

  it("shows the empty office-action state and hides record controls without permission", () => {
    render(<MantineProvider><OfficeActionsPage /></MantineProvider>);
    expect(screen.getByText("No office actions are recorded for this application.")).toBeInTheDocument();
    expect(screen.queryByText("Record office action")).not.toBeInTheDocument();
  });

  it("shows the office-action loading state", () => {
    hooks.useOfficeActions.mockReturnValue({ data: undefined, isPending: true, error: null });
    render(<MantineProvider><OfficeActionsPage /></MantineProvider>);
    expect(screen.getByText("Loading office actions…")).toBeInTheDocument();
  });

  it("shows API errors for office-action retrieval", () => {
    hooks.useOfficeActions.mockReturnValue({
      data: undefined, isPending: false,
      error: { response: { data: { error: { message: "Office-action service unavailable" } } } },
    });
    render(<MantineProvider><OfficeActionsPage /></MantineProvider>);
    expect(screen.getByText("Office-action service unavailable")).toBeInTheDocument();
  });
});
