import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { RestorationRequest } from "../api/types";
import RestorationsPage from "./RestorationsPage";

const authMock = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));
vi.mock("../../../auth/AuthProvider", () => authMock);

const hooks = vi.hoisted(() => ({
  useRestorations: vi.fn(),
  useCreateRestoration: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleRestoration: RestorationRequest = {
  id: 1,
  requester_user_id: 10,
  department: "CSE",
  archival_request_id: 5,
  classification: "Routine",
  target_destination: "/var/recovery/cse",
  status: "submitted",
  approved_by_user_id: null,
  approved_at: null,
  executed_by_user_id: null,
  restored_at: null,
  error_message: "",
  created_at: "2026-11-21T11:00:00Z",
};

describe("RestorationsPage", () => {
  const createMutate = vi.fn();

  beforeEach(() => {
    authMock.useAuth.mockReturnValue({
      can: (perm: string) => perm === "badms.restoration.create",
    });
    hooks.useRestorations.mockReturnValue({
      data: { results: [sampleRestoration] },
      isPending: false,
      error: null,
    });
    hooks.useCreateRestoration.mockReturnValue({
      mutate: createMutate,
      isPending: false,
    });
  });

  it("renders restorations and allows submitting restoration request", () => {
    render(
      <MantineProvider>
        <RestorationsPage />
      </MantineProvider>
    );

    expect(screen.getByText("Data Restorations")).toBeInTheDocument();
    expect(screen.getByText("/var/recovery/cse")).toBeInTheDocument();

    const openBtn = screen.getByRole("button", { name: /new restoration request/i });
    expect(openBtn).toBeInTheDocument();
    fireEvent.click(openBtn);

    expect(screen.getByText("Submit Data Restoration Request")).toBeInTheDocument();

    const targetInput = screen.getByLabelText(/target destination/i);
    fireEvent.change(targetInput, { target: { value: "/mnt/backup/restore" } });

    const submitBtn = screen.getByRole("button", { name: /submit request/i });
    fireEvent.click(submitBtn);

    expect(createMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        target_destination: "/mnt/backup/restore",
      }),
      expect.any(Object)
    );
  });
});
