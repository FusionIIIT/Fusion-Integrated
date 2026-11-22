import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SystemParameter } from "../api/types";
import SystemPolicyPage from "./SystemPolicyPage";

const hooks = vi.hoisted(() => ({
  useSystemParameters: vi.fn(),
  useUpdateSystemParameter: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleParam: SystemParameter = {
  id: 1,
  parameter_key: "SESSION_IDLE_TIMEOUT_MINUTES",
  parameter_value: { minutes: 15 },
  version: 1,
  effective_from: "2026-01-01T00:00:00Z",
  effective_to: null,
  is_active: true,
  updated_by_user_id: 1,
  created_at: "2026-01-01T00:00:00Z",
};

describe("SystemPolicyPage", () => {
  beforeEach(() => {
    const idle = { mutate: vi.fn(), isPending: false };
    hooks.useSystemParameters.mockReturnValue({
      data: [sampleParam],
      isLoading: false,
      isError: false,
    });
    hooks.useUpdateSystemParameter.mockReturnValue(idle);
  });

  it("renders system parameter configuration table", () => {
    render(
      <MantineProvider>
        <SystemPolicyPage />
      </MantineProvider>
    );

    expect(screen.getByText("System Parameter Policies")).toBeInTheDocument();
    expect(screen.getByText("SESSION_IDLE_TIMEOUT_MINUTES")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /configure parameter/i })).toBeInTheDocument();
  });
});
