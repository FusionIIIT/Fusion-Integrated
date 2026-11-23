import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminPage from "./AdminPage";

const hooks = vi.hoisted(() => ({
  usePmsConfiguration: vi.fn(), useAttorneyPanel: vi.fn(),
  usePmsAction: vi.fn(() => ({ mutate: vi.fn(), isPending: false, error: null })),
}));
const auth = vi.hoisted(() => ({ can: vi.fn() }));
vi.mock("../api/hooks", () => hooks);
vi.mock("../../../auth/AuthProvider", () => ({ useAuth: () => auth }));

function renderPage() {
  return render(<MantineProvider><MemoryRouter><AdminPage /></MemoryRouter></MantineProvider>);
}

describe("AdminPage", () => {
  beforeEach(() => {
    auth.can.mockReturnValue(false);
    hooks.usePmsConfiguration.mockReturnValue({ data: [], isPending: false, error: null });
    hooks.useAttorneyPanel.mockReturnValue({ data: [], isPending: false, error: null });
  });

  it("shows the unprivileged state without configuration or panel controls", () => {
    renderPage();
    expect(screen.getByText(/does not expose a role-assignment endpoint/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save policy value" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add attorney" })).not.toBeInTheDocument();
  });

  it("shows loading and API failure for policy configuration", () => {
    auth.can.mockImplementation((permission: string) => permission === "pms.config.manage");
    hooks.usePmsConfiguration.mockReturnValue({ data: undefined, isPending: true, error: null });
    const { rerender } = renderPage();
    expect(screen.getByText("Loading configured policies…")).toBeInTheDocument();
    hooks.usePmsConfiguration.mockReturnValue({
      data: undefined, isPending: false,
      error: { response: { data: { error: { message: "Configuration unavailable" } } } },
    });
    rerender(<MantineProvider><MemoryRouter><AdminPage /></MemoryRouter></MantineProvider>);
    expect(screen.getByText("Configuration unavailable")).toBeInTheDocument();
  });

  it("renders the policy save action only with configuration permission", () => {
    auth.can.mockImplementation((permission: string) => permission === "pms.config.manage");
    renderPage();
    expect(screen.getByRole("button", { name: "Save policy value" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save policy value" })).toBeEnabled();
  });
});
