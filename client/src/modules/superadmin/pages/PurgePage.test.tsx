import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PurgeRequest } from "../api/types";
import PurgePage from "./PurgePage";

const hooks = vi.hoisted(() => ({
  usePurgeRequests: vi.fn(),
  useCreatePurgeRequest: vi.fn(),
  useAuthorizePurge: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const samplePurge: PurgeRequest = {
  id: 1,
  archive_record: 1,
  requested_by_user_id: 1,
  request_reason: "Retention limit reached",
  status: "PENDING",
  authorized_by_user_id: null,
  authorized_at: null,
  rejection_reason: "",
  created_at: "2026-11-01T00:00:00Z",
};

describe("PurgePage", () => {
  beforeEach(() => {
    const idle = { mutate: vi.fn(), isPending: false };
    hooks.usePurgeRequests.mockReturnValue({
      data: [samplePurge],
      isLoading: false,
      isError: false,
    });
    hooks.useCreatePurgeRequest.mockReturnValue(idle);
    hooks.useAuthorizePurge.mockReturnValue(idle);
  });

  it("renders dual-authorization purge table", () => {
    render(
      <MantineProvider>
        <PurgePage />
      </MantineProvider>
    );

    expect(screen.getByText("Purge Authorizations")).toBeInTheDocument();
    expect(screen.getByText("Retention limit reached")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Authorize Purge" })).toBeInTheDocument();
  });
});
