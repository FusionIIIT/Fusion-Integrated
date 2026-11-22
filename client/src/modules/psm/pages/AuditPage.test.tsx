// AuditPage tests: loading, empty, error, and rendered audit rows.
import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPsmPage } from "../testHelper";
import AuditPage from "./AuditPage";

describe("AuditPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderPsmPage(<AuditPage />, ["psm.audit.view"]);
    expect(screen.getByRole("heading", { name: /audit trail/i })).toBeInTheDocument();
  });

  it("renders empty state when no audit rows exist", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    renderPsmPage(<AuditPage />, ["psm.audit.view"]);
    await waitFor(() => expect(screen.getByText(/no audit records found/i)).toBeInTheDocument());
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Audit error" } } } });
    renderPsmPage(<AuditPage />, ["psm.audit.view"]);
    await waitFor(() => expect(screen.getByText(/audit error/i)).toBeInTheDocument());
  });

  it("renders audit trail entries", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: {
        results: [{
          id: 1, actor_user_id: 5, actor_role: "ps_admin", action: "po.issued",
          target_type: "purchase_order", target_id: 9, from_state: "", to_state: "issued",
          details: {}, created_at: "2026-11-22T10:00:00Z",
        }],
      },
    });
    renderPsmPage(<AuditPage />, ["psm.audit.view"]);
    await waitFor(() => expect(screen.getByText("po.issued")).toBeInTheDocument());
  });
});
