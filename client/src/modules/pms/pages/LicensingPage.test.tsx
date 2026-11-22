import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LicensingPage from "./LicensingPage";

const hooks = vi.hoisted(() => ({
  useLicensingRequests: vi.fn(),
  usePmsAction: vi.fn(() => ({ mutate: vi.fn(), isPending: false, error: null })),
}));
const auth = vi.hoisted(() => ({ can: vi.fn() }));
vi.mock("../api/hooks", () => hooks);
vi.mock("../../../auth/AuthProvider", () => ({ useAuth: () => auth }));
vi.mock("../components/PmsApplicationSelect", () => ({
  PmsApplicationSelect: ({ onChange }: { onChange: (id: string) => void }) => (
    <button onClick={() => onChange("41")}>Select application</button>
  ),
}));

describe("LicensingPage (UC-PMS-022)", () => {
  beforeEach(() => {
    auth.can.mockReturnValue(false);
    hooks.useLicensingRequests.mockReturnValue({ data: [], isPending: false, error: null });
  });

  it("shows an empty result and hides the submission control without permission", () => {
    render(<MantineProvider><LicensingPage /></MantineProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Select application" }));
    expect(screen.getByText("No licensing requests")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Submit request" })).not.toBeInTheDocument();
  });

  it("shows request loading and API error states", () => {
    hooks.useLicensingRequests.mockReturnValue({ data: undefined, isPending: true, error: null });
    const { rerender, container } = render(<MantineProvider><LicensingPage /></MantineProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Select application" }));
    expect(container.querySelector(".mantine-Loader-root")).toBeInTheDocument();
    hooks.useLicensingRequests.mockReturnValue({
      data: undefined, isPending: false,
      error: { response: { data: { error: { message: "Licensing service unavailable" } } } },
    });
    rerender(<MantineProvider><LicensingPage /></MantineProvider>);
    expect(screen.getByText("Licensing service unavailable")).toBeInTheDocument();
  });

  it("shows the request action when licensing submission is permitted", () => {
    auth.can.mockImplementation((permission: string) => permission === "pms.licensing.submit");
    render(<MantineProvider><LicensingPage /></MantineProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Select application" }));
    expect(screen.getByRole("button", { name: "Submit request" })).toBeInTheDocument();
  });
});
