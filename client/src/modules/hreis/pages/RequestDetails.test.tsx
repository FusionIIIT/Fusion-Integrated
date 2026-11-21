import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RequestDetailsContent } from "./RequestDetails";

const hooks = vi.hoisted(() => ({ useRequestDetails: vi.fn() }));
vi.mock("../api/hooks", () => hooks);

function show() {
  render(<MantineProvider><RequestDetailsContent id={42} /></MantineProvider>);
}

describe("Request history", () => {
  it("shows loading and empty history states", () => {
    hooks.useRequestDetails.mockReturnValue({ isPending: true });
    const mounted = render(<MantineProvider><RequestDetailsContent id={42} /></MantineProvider>);
    expect(screen.getByText("Loading request history...")).toBeInTheDocument();
    mounted.unmount();
    hooks.useRequestDetails.mockReturnValue({ data: { state: "submitted", payload: {}, history: [] } });
    show();
    expect(screen.getByText("No workflow history is recorded.")).toBeInTheDocument();
  });

  it("shows access errors without disclosing request data", () => {
    hooks.useRequestDetails.mockReturnValue({ error: {
      response: { status: 404, data: { error: { message: "No accessible HR request was found." } } },
    } });
    show();
    expect(screen.getByText("No accessible HR request was found.")).toBeInTheDocument();
    expect(screen.queryByText("Submitted information")).not.toBeInTheDocument();
  });

  it("renders ordered authority and financial history with escaped evidence", () => {
    hooks.useRequestDetails.mockReturnValue({ data: {
      state: "financial_processing_recorded", payload: { purpose: "Synthetic" },
      history: [{ event: "approve", target: "approved", acting_designation: "Registrar",
        reason: "<script>synthetic evidence</script>", recorded_at: "2026-11-22T00:00:00Z" }],
      claim_summary: { status_history: [{ payment_status: "paid", source_system: "finance",
        external_status_reference: "SYNTHETIC-REFERENCE", recorded_at: "2026-11-22T01:00:00Z" }] },
    } });
    show();
    expect(screen.getByText("approve — approved")).toBeInTheDocument();
    expect(screen.getByText("Acting role: Registrar")).toBeInTheDocument();
    expect(screen.getByText("<script>synthetic evidence</script>")).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
    expect(screen.getByText("finance: SYNTHETIC-REFERENCE")).toBeInTheDocument();
  });
});
