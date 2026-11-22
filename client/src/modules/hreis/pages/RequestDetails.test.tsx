import { boundary, resetBoundary, show } from "./testSupport";
import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { RequestDetailsContent } from "./RequestDetails";

describe("Request history through HTTP", () => {
  beforeEach(resetBoundary);
  it("shows loading and empty history states", async () => {
    boundary.get.mockImplementation(() => new Promise(() => {}));
    const mounted = show(<RequestDetailsContent id={42} />);
    expect(screen.getByText("Loading request history...")).toBeInTheDocument();
    mounted.unmount();
    boundary.get.mockResolvedValue({ data: { state: "submitted", payload: {}, history: [] } });
    show(<RequestDetailsContent id={42} />);
    expect(await screen.findByText("No workflow history is recorded.")).toBeInTheDocument();
    expect(boundary.get).toHaveBeenCalledWith("/hreis/requests/42/");
  });
  it("shows access errors without disclosing request data", async () => {
    boundary.get.mockRejectedValue({ response: { status: 404,
      data: { error: { message: "No accessible HR request was found." } } } });
    show(<RequestDetailsContent id={42} />);
    expect(await screen.findByText("No accessible HR request was found.")).toBeInTheDocument();
    expect(screen.queryByText("Submitted information")).toBeNull();
  });
  it("renders authority, unavailable status and later financial history with escaped evidence", async () => {
    boundary.get.mockResolvedValue({ data: {
      state: "financial_processing_recorded", payload: { purpose: "Synthetic" },
      history: [{ event: "approve", target: "approved", acting_designation: "Registrar",
        reason: "<script>synthetic evidence</script>", recorded_at: "2026-11-22T00:00:00Z" }],
      claim_summary: { status_history: [
        { payment_status: null, source_system: null, external_status_reference: null, recorded_at: "2026-11-22T00:00:00Z" },
        { payment_status: "paid", source_system: "finance", external_status_reference: "SYNTHETIC-REFERENCE", recorded_at: "2026-11-22T01:00:00Z" },
      ] },
    } });
    show(<RequestDetailsContent id={42} />);
    expect(await screen.findByText("approve — approved")).toBeInTheDocument();
    expect(screen.getByText("Acting role: Registrar")).toBeInTheDocument();
    expect(screen.getByText("<script>synthetic evidence</script>")).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
    expect(screen.getByText("External status unavailable")).toBeInTheDocument();
    expect(screen.getByText("finance: SYNTHETIC-REFERENCE")).toBeInTheDocument();
  });
});
