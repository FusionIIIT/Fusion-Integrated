import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SecurityPolicy } from "../api/types";
import SecurityPoliciesPage from "./SecurityPoliciesPage";

const hooks = vi.hoisted(() => ({
  useSecurityPolicies: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const samplePolicy: SecurityPolicy = {
  id: 1,
  policy_key: "AES_KEY_EXPIRY_DAYS",
  policy_value: { days: 90 },
  configured_by_user_id: 2,
  effective_from: "2026-11-01T00:00:00Z",
  effective_to: null,
  is_active: true,
  created_at: "2026-11-01T00:00:00Z",
};

describe("SecurityPoliciesPage", () => {
  beforeEach(() => {
    hooks.useSecurityPolicies.mockReturnValue({
      data: { results: [samplePolicy] },
      isPending: false,
      error: null,
    });
  });

  it("renders security policy table with active policies", () => {
    render(
      <MantineProvider>
        <SecurityPoliciesPage />
      </MantineProvider>
    );

    expect(screen.getByText("Security & Encryption Policies")).toBeInTheDocument();
    expect(screen.getByText("AES_KEY_EXPIRY_DAYS")).toBeInTheDocument();
  });
});
