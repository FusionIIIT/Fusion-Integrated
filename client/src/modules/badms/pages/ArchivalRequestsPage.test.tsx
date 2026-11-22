import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ArchivalRequest } from "../api/types";
import ArchivalRequestsPage from "./ArchivalRequestsPage";

const authMock = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));
vi.mock("../../../auth/AuthProvider", () => authMock);

const hooks = vi.hoisted(() => ({
  useArchivalRequests: vi.fn(),
  useCreateArchivalRequest: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleArchival: ArchivalRequest = {
  id: 1,
  requester_user_id: 10,
  department: "CSE",
  file_name: "grades_2025.zip",
  file_type: "application/zip",
  file_size_bytes: 5242880,
  reason: "Regulatory semester archival",
  file_storage_path: "/data/cse/grades_2025.zip",
  initial_classification: "Sensitive",
  authoritative_classification: "Sensitive",
  status: "submitted",
  hod_reviewed_by_user_id: null,
  hod_decision_at: null,
  hod_remarks: "",
  sysadmin_classified_by_user_id: null,
  classified_at: null,
  encryption_algorithm: "AES-256-GCM",
  is_encrypted: false,
  encrypted_by_user_id: null,
  encrypted_at: null,
  is_special_archival: false,
  retention_policy_ref: "Sensitive-365d",
  created_at: "2026-11-20T10:00:00Z",
};

describe("ArchivalRequestsPage", () => {
  const createMutate = vi.fn();

  beforeEach(() => {
    authMock.useAuth.mockReturnValue({
      can: (perm: string) => perm === "badms.archival.create",
    });
    hooks.useArchivalRequests.mockReturnValue({
      data: { results: [sampleArchival] },
      isPending: false,
      error: null,
    });
    hooks.useCreateArchivalRequest.mockReturnValue({
      mutate: createMutate,
      isPending: false,
    });
  });

  it("renders archival requests and opens submission modal", () => {
    render(
      <MantineProvider>
        <ArchivalRequestsPage />
      </MantineProvider>
    );

    expect(screen.getByText("Secure Archival Requests")).toBeInTheDocument();
    expect(screen.getByText("grades_2025.zip")).toBeInTheDocument();

    const openBtn = screen.getByRole("button", { name: /new archival request/i });
    expect(openBtn).toBeInTheDocument();
    fireEvent.click(openBtn);

    expect(screen.getByText("Submit Secure Archival Request")).toBeInTheDocument();
  });

  it("submits the archival request form", () => {
    render(
      <MantineProvider>
        <ArchivalRequestsPage />
      </MantineProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: /new archival request/i }));

    const fileNameInput = screen.getByLabelText(/file name/i);
    const storagePathInput = screen.getByLabelText(/storage path/i);
    const reasonInput = screen.getByLabelText(/reason for archival/i);

    fireEvent.change(fileNameInput, { target: { value: "dataset_2026.zip" } });
    fireEvent.change(storagePathInput, { target: { value: "/data/cse/dataset.zip" } });
    fireEvent.change(reasonInput, { target: { value: "Annual audit backup" } });

    const submitBtn = screen.getByRole("button", { name: /submit request/i });
    fireEvent.click(submitBtn);

    expect(createMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        file_name: "dataset_2026.zip",
        file_storage_path: "/data/cse/dataset.zip",
        reason: "Annual audit backup",
      }),
      expect.any(Object)
    );
  });
});
