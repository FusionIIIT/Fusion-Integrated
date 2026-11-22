import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { BonafideRequest } from "../api/types";
import BonafidePage from "./BonafidePage";

const hooks = vi.hoisted(() => ({
  useBonafides: vi.fn(),
  useSubmitBonafide: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const auth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: auth,
}));

const sampleBonafide: BonafideRequest = {
  id: 1,
  certificate_number: "BONA-2026-0001",
  student_id: "24BCS205",
  purpose: "GENERAL",
  details: "Need for scholarship",
  status: "APPROVED",
  issued_by: "ACADEMIC_ADMIN",
  issued_at: "2026-11-21T10:00:00Z",
  created_at: "2026-11-20T10:00:00Z",
};

describe("BonafidePage", () => {
  beforeEach(() => {
    auth.mockReturnValue({
      can: () => true,
      session: {
        user: { username: "24BCS205", display_name: "Rahul Kumar" },
      },
    });
    hooks.useBonafides.mockReturnValue({
      data: { results: [sampleBonafide] },
      isPending: false,
      error: null,
    });
    hooks.useSubmitBonafide.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({ id: 2 }),
      isPending: false,
    });
  });

  it("renders certificate list", () => {
    render(
      <MantineProvider>
        <BonafidePage />
      </MantineProvider>,
    );

    expect(screen.getByText("Bonafide Certificates")).toBeInTheDocument();
    expect(screen.getByText("BONA-2026-0001")).toBeInTheDocument();
    expect(screen.getByText("Need for scholarship")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /request certificate/i })).toBeInTheDocument();
  });
});
