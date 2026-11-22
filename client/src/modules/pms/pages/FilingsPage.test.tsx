import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { application } from "./pageTestFixtures";
import FilingsPage from "./FilingsPage";

const hooks = vi.hoisted(() => ({
  usePmsApplication: vi.fn(),
  usePmsAction: vi.fn(() => ({ mutate: vi.fn(), isPending: false, error: null })),
}));
const auth = vi.hoisted(() => ({ can: vi.fn(), session: { user: { id: 1001 } } }));
vi.mock("../api/hooks", () => hooks);
vi.mock("../../../auth/AuthProvider", () => ({ useAuth: () => auth }));
vi.mock("../components/PmsApplicationSelect", () => ({
  PmsApplicationSelect: ({ onChange }: { onChange: (id: string) => void }) => (
    <button onClick={() => onChange("41")}>Select application</button>
  ),
}));

function renderPage() {
  return render(<MantineProvider><MemoryRouter><FilingsPage /></MemoryRouter></MantineProvider>);
}

describe("FilingsPage (UC-PMS-010, UC-PMS-011)", () => {
  beforeEach(() => {
    auth.can.mockReturnValue(false);
    hooks.usePmsApplication.mockReturnValue({ data: application, isPending: false, error: null });
  });

  it("shows loading and error states", () => {
    hooks.usePmsApplication.mockReturnValue({ data: undefined, isPending: true, error: null });
    const { rerender } = renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Select application" }));
    expect(screen.getByText("Loading application…")).toBeInTheDocument();
    hooks.usePmsApplication.mockReturnValue({
      data: undefined, isPending: false,
      error: { response: { data: { error: { message: "Application unavailable" } } } },
    });
    rerender(<MantineProvider><MemoryRouter><FilingsPage /></MemoryRouter></MantineProvider>);
    expect(screen.getByText("Application unavailable")).toBeInTheDocument();
  });

  it("keeps filing and prior-art actions hidden without their permissions", () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Select application" }));
    expect(screen.getByText(/PMS-2026-00041 · Thermal storage controller/)).toBeInTheDocument();
    expect(screen.queryByText("Record external filing")).not.toBeInTheDocument();
    expect(screen.queryByText(/Prior-art search is not available/)).not.toBeInTheDocument();
  });

  it("exposes filing actions to users with filing permission", () => {
    auth.can.mockImplementation((permission: string) => permission === "pms.filing.record");
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Select application" }));
    expect(screen.getByRole("button", { name: "Record filing" })).toBeInTheDocument();
  });
});
