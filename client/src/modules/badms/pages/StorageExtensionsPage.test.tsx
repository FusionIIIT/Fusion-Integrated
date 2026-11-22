import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { StorageExtensionRequest } from "../api/types";
import StorageExtensionsPage from "./StorageExtensionsPage";

const authMock = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));
vi.mock("../../../auth/AuthProvider", () => authMock);

const hooks = vi.hoisted(() => ({
  useStorageExtensions: vi.fn(),
  useCreateStorageExtension: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleExtension: StorageExtensionRequest = {
  id: 1,
  requester_user_id: 10,
  department: "CSE",
  current_usage_bytes: 85899345920,
  current_quota_bytes: 107374182400,
  requested_extension_bytes: 21474836480,
  justification: "Capstone project storage",
  status: "submitted",
  hod_reviewed_by_user_id: null,
  hod_decision_at: null,
  hod_remarks: "",
  created_at: "2026-11-21T09:00:00Z",
};

describe("StorageExtensionsPage", () => {
  const createMutate = vi.fn();

  beforeEach(() => {
    authMock.useAuth.mockReturnValue({
      can: (perm: string) => perm === "badms.storage.create",
    });
    hooks.useStorageExtensions.mockReturnValue({
      data: { results: [sampleExtension] },
      isPending: false,
      error: null,
    });
    hooks.useCreateStorageExtension.mockReturnValue({
      mutate: createMutate,
      isPending: false,
    });
  });

  it("renders storage extension requests and allows requesting extension", () => {
    render(
      <MantineProvider>
        <StorageExtensionsPage />
      </MantineProvider>
    );

    expect(screen.getByText("Storage Extension Requests")).toBeInTheDocument();
    expect(screen.getByText("80.00 GB")).toBeInTheDocument();

    const openBtn = screen.getByRole("button", { name: /request extension/i });
    expect(openBtn).toBeInTheDocument();
    fireEvent.click(openBtn);

    expect(screen.getByText("Request Storage Quota Extension")).toBeInTheDocument();

    const justificationInput = screen.getByLabelText(/business justification/i);
    fireEvent.change(justificationInput, { target: { value: "Need extra 15GB" } });

    const submitBtn = screen.getByRole("button", { name: /submit request/i });
    fireEvent.click(submitBtn);

    expect(createMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        justification: "Need extra 15GB",
      }),
      expect.any(Object)
    );
  });
});
