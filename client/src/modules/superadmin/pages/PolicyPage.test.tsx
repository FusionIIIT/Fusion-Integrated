import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PolicyParameter } from "../api/types";
import PolicyPage from "./PolicyPage";

const hooks = vi.hoisted(() => ({
  usePolicyParams: vi.fn(),
  useSupersedePolicyParam: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleParam: PolicyParameter = {
  id: 1,
  key: "archival.reversibility_window_days",
  value: "30",
  value_type: "integer",
  version: 1,
  effective_from: "2026-11-01T00:00:00Z",
  effective_to: null,
  description: "Days before archival is finalized",
  updated_by: 1,
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
};

describe("PolicyPage", () => {
  const mockSupersede = { mutate: vi.fn(), isPending: false };

  beforeEach(() => {
    vi.restoreAllMocks();
    mockSupersede.mutate.mockReset();
    hooks.useSupersedePolicyParam.mockReturnValue(mockSupersede);
  });

  it("renders loader during loading state", () => {
    hooks.usePolicyParams.mockReturnValue({
      data: null,
      isPending: true,
      error: null,
    });

    const { container } = render(
      <MantineProvider>
        <PolicyPage />
      </MantineProvider>,
    );
    expect(container.querySelector(".mantine-Loader-root")).toBeInTheDocument();
  });

  it("renders empty state placeholder when no policy params exist", () => {
    hooks.usePolicyParams.mockReturnValue({
      data: { count: 0, next: null, previous: null, results: [] },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <PolicyPage />
      </MantineProvider>,
    );
    expect(screen.getByText("No policy parameters seeded")).toBeInTheDocument();
  });

  it("renders error state on 500 failure", () => {
    hooks.usePolicyParams.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Policy fetch error 500"),
    });

    render(
      <MantineProvider>
        <PolicyPage />
      </MantineProvider>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("renders parameters and allows superseding a parameter", async () => {
    hooks.usePolicyParams.mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [sampleParam] },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <PolicyPage />
      </MantineProvider>,
    );

    expect(screen.getByText("archival.reversibility_window_days")).toBeInTheDocument();
    expect(screen.getByText("v1")).toBeInTheDocument();

    const supersedeBtn = screen.getByRole("button", { name: "Supersede" });
    expect(supersedeBtn).toBeInTheDocument();
    fireEvent.click(supersedeBtn);

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toBeInTheDocument();

    const valueInput = within(dialog).getByLabelText(/^New value/i);
    fireEvent.change(valueInput, { target: { value: "45" } });

    fireEvent.click(within(dialog).getByRole("button", { name: "Supersede" }));

    expect(mockSupersede.mutate).toHaveBeenCalled();
  });
});
